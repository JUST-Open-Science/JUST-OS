# JUST-OS

This repository contains the source code for the [JUST-OS](https://just-open-science.github.io/) project.


## Installation

1. Install uv according to the instructions for your platform [here](https://docs.astral.sh/uv/getting-started/installation/)

2. Clone the repository:
```bash
git clone https://github.com/just-open-science/JUST-OS.git
cd JUST-OS
```
3. Download the vector store from [here](https://drive.google.com/file/d/1kgAvRN3OQ0UjkFmBXXtJcHIiFbcslJIl/view?usp=drive_link) and extract it to `data/interim`.

4. Create an `.env` file with your UG-LLM api key like
```
RUGLLM_API_KEY=<your key>
``` 

5. Start the app with:
```bash
uv run app.py
```

or in production with
```
uv run gunicorn -w 4 -b 127.0.0.1:5000 app:app
```
