# app.py
from flask import Flask, render_template, request, Response
import json
from config import WELCOME_MESSAGE
from qualle import Qualle
import yaml


class FlaskApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.rag_service = None
        self.setup_routes()

    def setup_routes(self):
        @self.app.route("/")
        def home():
            return render_template("index.html", welcome_message=WELCOME_MESSAGE)

        @self.app.route("/chat", methods=["POST"])
        def chat():
            user_message = request.json["message"]

            def generate():
                try:
                    for response in self.rag_service.get_response(user_message):
                        yield json.dumps(response) + "\n"

                except Exception as e:
                    print(f"Error: {str(e)}")
                    yield json.dumps(
                        {
                            "status": "error",
                            "message": "An error occurred while processing your request.",
                        }
                    ) + "\n"

            return Response(generate(), mimetype="text/event-stream")

    def create_app(self, config):
        self.rag_service = Qualle(config)
        return self.app


def load_config():
    with open("config.yaml", "r") as config_file:
        return yaml.safe_load(config_file)


if __name__ == "__main__":
    config = load_config()
    flask_app = FlaskApp()
    app = flask_app.create_app(config)
    app.run(debug=True, port=config["server_port"])
