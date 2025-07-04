import json
import logging

import yaml
from flask import Flask, Response, render_template, request
from redis import Redis

from just_os.chat_manager import ChatManager
from just_os.extensions import flask_static_digest

logger = logging.getLogger(__name__)


class FlaskApp:
    def __init__(self):
        self.app = Flask(__name__, static_folder="../public", static_url_path="")
        self.chat_manager = ChatManager(Redis(host="redis", port=6379, db=0))
        self._rag_service = None
        self.setup_routes()

    def setup_routes(self):
        @self.app.route("/")
        def home():
            return render_template("index.html")

        @self.app.route("/chat", methods=["POST"])
        def chat():
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
        self.app.config.from_object("config.settings")
        flask_static_digest.init_app(self.app)
        return self.app


flask_app = FlaskApp()
app = flask_app.create_app()
