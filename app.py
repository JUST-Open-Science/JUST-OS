import json
import logging

import yaml
from flask import Flask, Response, render_template, request
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore
from redis import Redis

from chat_manager import ChatManager
from qualle import Qualle

logger = logging.getLogger(__name__)


class FlaskApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.chat_manager = ChatManager(Redis(host="localhost", port=6379, db=0))
        self._embed_model = None
        self._retriever = None
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

        logger.debug("Initializing components")
        self._embed_model = HuggingFaceEmbedding(model_name=config["embedding_model"])
        persist_dir = config["vector_store"]
        vector_store = FaissVectorStore.from_persist_dir(persist_dir)
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store, persist_dir=persist_dir
        )
        index = load_index_from_storage(
            storage_context=storage_context, embed_model=self._embed_model
        )
        self._retriever = index.as_retriever(similarity_top_k=config["retriever_top_k"])

        self.rag_service = Qualle(
            config, self.chat_manager, self._embed_model, self._retriever
        )
        return self.app


def load_config():
    with open("config.yaml", "r") as config_file:
        return yaml.safe_load(config_file)


config = load_config()
flask_app = FlaskApp()
app = flask_app.create_app(config)


if __name__ == "__main__":
    app.run(debug=True, port=config["server_port"])
