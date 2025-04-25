import json

import yaml
from flask import Flask, Response, render_template, request

from qualle import Qualle
from chat_manager import ChatManager
from redis import Redis


class FlaskApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.chat_manager = ChatManager(Redis(host="localhost", port=6379, db=0))
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
                    for response in self.rag_service.get_response(
                        user_message, chat_id
                    ):
                        yield json.dumps(response) + "\n"

                except Exception as e:
                    print(f"Error: {str(e)}")
                    print(response)
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

    def create_app(self, config):
        self.config = config
        self.rag_service = Qualle(config, self.chat_manager)
        return self.app


def load_config():
    with open("config.yaml", "r") as config_file:
        return yaml.safe_load(config_file)


config = load_config()
flask_app = FlaskApp()
app = flask_app.create_app(config)


if __name__ == "__main__":
    app.run(debug=True, port=config["server_port"])
