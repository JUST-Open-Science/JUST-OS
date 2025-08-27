# JUST-OS

This repository contains the source code for the [JUST-OS](https://just-open-science.github.io/) project.


## Installation

1. Make sure your system has both `docker` and `docker-compose` installed
2. Depending on your setup, create a symlink `compose.override.yaml` to either `compose.dev.yaml` or `compose.prod.yaml`. In the development environment the web server will automatically restart after changes to the code.
```
ln -s <compose.dev.yaml or compose.prod.yaml> compose.override.yaml
```
3. Copy `.env.example` to `.env` and fill in the required variables.
4. Start the docker containers with `docker compose up`.

## Ingestion Pipeline

The ingestion process creates a vector store in the `data` folder that the backend will use. Follow these steps in order:

1. **Filter resources on Open Access status as assessed by Unpaywall**:
   ```bash
   uv run bootstrap_local_database.py
   ```

2. **Convert PDFs to Markdown**:
   ```bash
   ./marker.sh
   ```

3. **Generate embeddings**:
   ```bash
   uv run embed.py
   ```

## Acknowledgements
The development of the application benefitted greatly from the following open source software and public resources:
- Allen Institue for AI's [OpenScholar model](https://huggingface.co/OpenSciLM/Llama-3.1_OpenScholar-8B) and [associated software](https://github.com/AkariAsai/OpenScholar)
- Sebastian Mathot's [Sigmund repository](https://github.com/open-cogsci/sigmund-ai)
- The [Unpaywall API](https://unpaywall.org/products/api)
- [This](https://github.com/nickjj/docker-flask-example) example Docker + Flask web app
