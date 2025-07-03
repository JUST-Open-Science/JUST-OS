from llama_index.indices.managed.bge_m3 import BGEM3Index
from openai import Client
from tqdm import tqdm

MODEL = "mistralai/Mistral-Nemo-Instruct-2407"

SYTEM_PROMPT = ""


def context_from_nodes(nodes):
    return "\n\n".join(
        f"### Source {idx}\n{node.text}"
        for idx, node in enumerate(nodes, start=1)
    )


if __name__ == "__main__":
    client = Client(base_url="http://localhost:8000/v1", api_key="EMPTY")

    index = BGEM3Index.load_from_disk(
        "storage_m3", weights_for_different_modes=[0.6, 0.4, 0.0]
    )

    retriever = index.as_retriever(similarity_top_k=5)
    prompt_template = """
Please provide an answer based solely on the provided sources.
When referencing information from a source,
cite the appropriate source(s) using their corresponding numbers.
Every answer should include at least one source citation.
Only cite a source when you are explicitly referencing it.
If none of the sources are helpful, you should indicate that.
For example:
Source 1:
The sky is red in the evening and blue in the morning.
Source 2:
Water is wet when the sky is red.
Query: When is water wet?
Answer: Water will be wet when the sky is red [2],
which occurs in the evening [1]
Now it's your turn. Below are several numbered sources of information:
------
{context_items}
```
Given the context information, answer the query.
Do not base your answer on information outside of the provided context. If the provided context does not contain any relevant information, reply with something along the lines of "Sorry, I can't help you with that."
In your answer, don't mention term like 'context' or 'context item' when referring to the items above. Example: rather than "Based on the provided context ...", say "Based on my knowledge ...".
Query: {query}
    """

    queries = [
        "What is preregistration and why is it important?",
        "How do I preregister my longitudinal research?",
        "How do I preregister qualitative research?",
        "Where can I preregister my research?",
        "How is preregistration different from registered report?",
        "How is preregistration different from a registered clinical trial?",
        "Will people find my preregistration?",
        "What is open access and what are advantages and disadvantages?",
        "How can I make sure nobody misuses my openly available data?",
        "What are the best platforms and tools for sharing research data openly?",
        "How does open access publishing impact the dissemination and citation of research?",
        "What are the legal and ethical considerations in sharing human subject data?",
        "How does open science reshape the future of interdisciplinary and collaborative research?",
    ]

    for query in tqdm(queries):
        nodes = retriever.retrieve(query)
        context = context_from_nodes(nodes)
        prompt = prompt_template.format(context_items=context, query=query)

        response = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.2
        )
        print("-QUERY----------------------------")
        print(query)
        print("-PROMPT---------------------------")
        print(prompt)
        print("-RESPONSE-------------------------")
        print(response.choices[0].message.content)
