import json
import logging
import os
import secrets
from typing import Dict, Any, Optional, Generator, Union

from flask import Flask, Response, render_template, request, session, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import TooManyRequests

from config.settings import get_config
from just_os.chat_manager import ChatManager
from just_os.extensions import flask_static_digest

logger = logging.getLogger(__name__)


class RateLimitManager:
    """
    Manages rate limiting configuration and functionality.
    """

    def __init__(self, app: Flask, config: Dict[str, Any]):
        """
        Initialize rate limiting for the application.

        Args:
            app: Flask application instance
            config: Configuration dictionary
        """
        self.app = app
        self.config = config

        # Initialize rate limiter
        self.limiter = Limiter(
            key_func=self._get_rate_limit_key,
            app=self.app,
            default_limits=self._get_default_rate_limits(),
            storage_uri=f"redis://{config['REDIS_HOST']}:{config['REDIS_PORT']}/{config['REDIS_DB']}",
            strategy="fixed-window",
        )

        # Register error handler for rate limit exceeded
        self.app.errorhandler(429)(self._handle_rate_limit_exceeded)

    def _get_rate_limit_key(self):
        """
        Custom key function for rate limiting that uses both IP and session ID.
        This provides more accurate rate limiting for users behind shared IPs.
        
        For cross-origin requests (where cookies won't work), also accepts
        session_id from the request body.

        Returns:
            str: Rate limit key combining IP address and session ID if available
        """
        # Get the IP address
        ip_address = get_remote_address()

        session_id = None
        
        # Try to get session_id from request body (works for cross-origin requests)
        if request.is_json and request.json:
            session_id = request.json.get('session_id')
        
        # Fall back to Flask session cookie if available
        if not session_id and "user_id" in session:
            session_id = session["user_id"]
        
        if session_id:
            return f"{ip_address}_{session_id}"
        return ip_address

    def get_chat_rate_limit(self) -> str:
        """
        Get the rate limit for the chat endpoint from config.

        Returns:
            str: Rate limit string in the format "X per minute/hour"
        """
        # Check if rate limits are defined in config
        if "RATE_LIMIT_MINUTE" in self.config:
            return f"{self.config['RATE_LIMIT_MINUTE']} per minute"
        if "RATE_LIMIT_HOUR" in self.config:
            return f"{self.config['RATE_LIMIT_HOUR']} per hour"

        # Default rate limit if not configured
        return "10 per minute"

    def _handle_rate_limit_exceeded(self, e: TooManyRequests):
        """
        Handle rate limit exceeded errors with a proper JSON response.

        Args:
            e: The TooManyRequests exception

        Returns:
            Response: JSON response with error details
        """
        response = jsonify(
            {
                "status": "error",
                "message": "Rate limit exceeded. Please try again later.",
                "retry_after": e.description,
            }
        )
        response.status_code = 429
        return response

    def _get_default_rate_limits(self) -> list:
        """
        Get the default rate limits from config.

        Returns:
            list: List of rate limit strings
        """
        limits = []

        # Add day limit if configured
        if "RATE_LIMIT_DAY" in self.config:
            limits.append(f"{self.config['RATE_LIMIT_DAY']} per day")
        else:
            limits.append("200 per day")

        # Add hour limit if configured
        if "RATE_LIMIT_HOUR" in self.config:
            limits.append(f"{self.config['RATE_LIMIT_HOUR']} per hour")
        else:
            limits.append("50 per hour")

        return limits


class FlaskApp:
    """
    Main Flask application class that handles routes and services.
    """

    def __init__(self):
        """Initialize the Flask application with all necessary components."""
        # Load configuration
        self.config = get_config()

        # Initialize Flask app
        self.app = Flask(__name__, static_folder="../public", static_url_path="")
        self.app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))
        self.app.config.update(self.config)

        # Initialize components
        self.chat_manager = ChatManager()
        self._rag_service = None

        # Initialize rate limiting
        self.rate_limit_manager = RateLimitManager(self.app, self.config)

        # Configure CORS for cross-origin API access
        self._configure_cors()

        # Set up routes
        self.setup_routes()

        logger.debug("Flask application initialized")

    def _configure_cors(self):
        """
        Configure CORS (Cross-Origin Resource Sharing) to allow
        specified origins to access the API.
        """
        allowed_origins = self.config.get("ALLOWED_ORIGINS", [])
        
        if allowed_origins:
            CORS(
                self.app,
                resources={
                    r"/chat": {
                        "origins": allowed_origins,
                        "methods": ["POST", "OPTIONS"],
                        "allow_headers": ["Content-Type"],
                    }
                },
            )
            logger.info(f"CORS enabled for origins: {allowed_origins}")
        else:
            logger.debug("CORS not configured - no ALLOWED_ORIGINS specified")

    def _validate_message(self, message: str) -> tuple[bool, Optional[str]]:
        """
        Validate the user's message.

        Args:
            message: The message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        max_length = self.config.get("MAX_MESSAGE_LENGTH", 2000)
        min_length = self.config.get("MIN_MESSAGE_LENGTH", 3)

        if len(message) < min_length:
            return False, f"Message too short (minimum {min_length} characters)"
        if len(message) > max_length:
            return False, f"Message too long (maximum {max_length} characters)"
        return True, None

    def setup_routes(self):
        """Set up all application routes."""

        @self.app.route("/")
        def home():
            """Home page route."""
            # Get background color from URL parameter, default to #fefdf6 if not provided
            bg_color = request.args.get("bg_color", "#fefdf6")

            # Validate the background color (simple validation for hex colors and named colors)
            import re

            if bg_color.startswith("#"):
                # Validate hex color format (#RGB, #RRGGBB, #RRGGBBAA)
                if not re.match(
                    r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$", bg_color
                ):
                    bg_color = "#fefdf6"  # Default if invalid

            return render_template("index.html", bg_color=bg_color)

        @self.app.route("/chat", methods=["POST"])
        @self.rate_limit_manager.limiter.limit(
            self.rate_limit_manager.get_chat_rate_limit
        )
        def chat():
            """
            Chat endpoint that processes user messages and returns responses.
            Uses server-sent events for streaming responses.
            """
            # Initialize session if not already done
            if "user_id" not in session:
                session["user_id"] = secrets.token_hex(8)
                logger.debug(f"Created new user session: {session['user_id']}")

            # Extract request data
            try:
                user_message = request.json["message"]
                chat_id = request.json["chat_id"]
            except (KeyError, TypeError) as e:
                logger.error(f"Invalid request data: {str(e)}")
                return jsonify(
                    {
                        "status": "error",
                        "message": "Invalid request data. 'message' and 'chat_id' are required.",
                    }
                ), 400

            # Validate message content
            is_valid, error_msg = self._validate_message(user_message)
            if not is_valid:
                logger.warning(f"Message validation failed: {error_msg}")
                return jsonify(
                    {
                        "status": "error",
                        "message": error_msg,
                    }
                ), 400

            return Response(
                self._generate_chat_response(user_message, chat_id),
                mimetype="text/event-stream",
            )

    def _generate_chat_response(
        self, user_message: str, chat_id: str
    ) -> Generator[str, None, None]:
        """
        Generate chat responses as a stream.

        Args:
            user_message: The user's message
            chat_id: The chat session ID

        Yields:
            JSON-encoded response chunks
        """
        try:
            # Lazy-load RAG service only when needed
            rag_service = self.get_rag_service()
            if rag_service:
                for response in rag_service.get_response(user_message, chat_id):
                    yield json.dumps(response) + "\n"
            else:
                yield (
                    json.dumps(
                        {
                            "status": "error",
                            "message": "RAG service is not available in this environment.",
                        }
                    )
                    + "\n"
                )

        except Exception as e:
            logger.error(f"Error processing chat request: {str(e)}")
            yield (
                json.dumps(
                    {
                        "status": "error",
                        "message": "An error occurred while processing your request.",
                    }
                )
                + "\n"
            )

    def get_rag_service(self):
        """
        Lazy-load the RAG service only when needed.

        Returns:
            The RAG service instance or None if initialization fails
        """
        if self._rag_service is None:
            try:
                from just_os.rag_service import create_rag_service

                self._rag_service = create_rag_service(self.config, self.chat_manager)
                logger.debug("RAG service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize RAG service: {str(e)}")
                return None

        return self._rag_service

    def create_app(self) -> Flask:
        """
        Finalize and return the Flask application instance.

        Returns:
            Flask: The configured Flask application
        """
        # Initialize extensions
        flask_static_digest.init_app(self.app)
        return self.app


def get_app():
    # Create application instance
    flask_app = FlaskApp()
    return flask_app.create_app()
