from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
import pandas as pd


if __name__ == "__main__":
    documents = SimpleDirectoryReader("../data/raw/main_articles").load_data()

    node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=128)
    nodes = node_parser.get_nodes_from_documents(documents, show_progress=False)
    df = pd.DataFrame.from_records((node.to_dict() for node in nodes))

    df.to_json(
        "../data/interim/chunked_paragraphs_241025.json", orient="records"
    )
