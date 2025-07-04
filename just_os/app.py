import json
import logging
import secrets

import yaml
from flask import Flask, Response, render_template, request, session, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from redis import Redis
from werkzeug.exceptions import TooManyRequests

from just_os.chat_manager import ChatManager
from just_os.extensions import flask_static_digest

logger = logging.getLogger(__name__)


class FlaskApp:
    def __init__(self):
        self.app = Flask(__name__, static_folder="../public", static_url_path="")
        self.app.secret_key = secrets.token_hex(16)  # Generate a secure secret key for sessions
        self.chat_manager = ChatManager(Redis(host="redis", port=6379, db=0))
        self._rag_service = None
        
        # Load configuration first to access rate limit settings
        self.app.config.from_object("config.settings")
        
        # Initialize rate limiter
        self.limiter = Limiter(
            key_func=self._get_rate_limit_key,  # Custom key function for rate limiting
            app=self.app,
            default_limits=self._get_default_rate_limits(),
            storage_uri="redis://redis:6379/0",
            strategy="fixed-window",  # Use fixed window strategy for rate limiting
        )
        
        # Register error handler for rate limit exceeded
        self.app.errorhandler(429)(self._handle_rate_limit_exceeded)
        
        self.setup_routes()

    def setup_routes(self):
        @self.app.route("/")
        def home():
            return render_template("index.html")

        @self.app.route("/chat", methods=["POST"])
        @self.limiter.limit(self._get_chat_rate_limit)  # Dynamic rate limit based on config
        def chat():
            # Initialize session if not already done
            if 'user_id' not in session:
                session['user_id'] = secrets.token_hex(8)
                
            user_message = request.json["message"]
            chat_id = request.json["chat_id"]

            def generate():
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
                    print(f"Error: {str(e)}")
                    yield (
                        json.dumps(
                            {
                                "status": "error",
                                "message": "An error occurred while processing your request.",
                            }
                        )
                        + "\n"
                    )

            return Response(generate(), mimetype="text/event-stream")

    def get_rag_service(self):
        """Lazy-load the RAG service only when needed"""
        if self._rag_service is None and self.app.config is not None:
            try:
                from just_os.rag_service import create_rag_service

                self._rag_service = create_rag_service(
                    self.app.config, self.chat_manager
                )
                logger.debug("RAG service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize RAG service: {str(e)}")
                return None

        return self._rag_service

    def create_app(self):
        # Config is already loaded in __init__
        flask_static_digest.init_app(self.app)
        return self.app
        
    def _get_rate_limit_key(self):
        """
        Custom key function for rate limiting that uses both IP and session ID.
        This provides more accurate rate limiting for users behind shared IPs.
        """
        # Get the IP address
        ip_address = get_remote_address()
        
        # Get the session ID if available, otherwise use IP only
        if 'user_id' in session:
            return f"{ip_address}_{session['user_id']}"
        return ip_address
    
    def _get_chat_rate_limit(self):
        """
        Get the rate limit for the chat endpoint from config or use default.
        """
        # Check if rate limits are defined in config
        if 'RATE_LIMIT_MINUTE' in self.app.config:
            return f"{self.app.config['RATE_LIMIT_MINUTE']} per minute"
        if 'RATE_LIMIT_HOUR' in self.app.config:
            return f"{self.app.config['RATE_LIMIT_HOUR']} per hour"
        
        # Default rate limit if not configured
        return "10 per minute"
    
    def _handle_rate_limit_exceeded(self, e):
        """
        Handle rate limit exceeded errors with a proper JSON response.
        """
        response = jsonify({
            "status": "error",
            "message": "Rate limit exceeded. Please try again later.",
            "retry_after": e.description
        })
        response.status_code = 429
        return response
        
    def _get_default_rate_limits(self):
        """
        Get the default rate limits from config or use hardcoded defaults.
        """
        limits = []
        
        # Add day limit if configured
        if 'RATE_LIMIT_DAY' in self.app.config:
            limits.append(f"{self.app.config['RATE_LIMIT_DAY']} per day")
        else:
            limits.append("200 per day")
            
        # Add hour limit if configured
        if 'RATE_LIMIT_HOUR' in self.app.config:
            limits.append(f"{self.app.config['RATE_LIMIT_HOUR']} per hour")
        else:
            limits.append("50 per hour")
            
        return limits


flask_app = FlaskApp()
app = flask_app.create_app()
