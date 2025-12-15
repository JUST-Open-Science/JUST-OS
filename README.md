# JUST-OS

This repository contains the source code for the [JUST-OS](https://www.just-os.org/) project.


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

## API Integration

JUST-OS provides an API that can be integrated into external websites. The API is currently configured to allow access from `https://forrt.org`.

### Endpoint

**POST `/chat`**

Send a message and receive a streaming response.

### Request

```json
{
  "message": "What is open science?",
  "chat_id": "unique-conversation-id",
  "session_id": "unique-user-session-id"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `message` | Yes | The user's question (3-2000 characters) |
| `chat_id` | Yes | UUID for conversation continuity (generate with `crypto.randomUUID()`) |
| `session_id` | No | UUID for rate limiting across sessions (recommended for better rate limit accuracy) |

### Response

The endpoint returns a Server-Sent Events stream with JSON objects:

```json
{"status": "processing", "message": "Searching knowledge base..."}
{"status": "complete", "message": "<formatted HTML response>"}
```

### Rate Limits

- 10 requests per minute
- 50 requests per hour  
- 200 requests per day

Rate limits are applied per IP address + session_id combination.

### Example JavaScript Implementation

```javascript
// Persist session_id across page loads for consistent rate limiting
const sessionId = localStorage.getItem('just-os-session') || crypto.randomUUID();
localStorage.setItem('just-os-session', sessionId);

// Chat ID should be unique per conversation
let chatId = crypto.randomUUID();

async function sendMessage(userMessage) {
  const response = await fetch('https://www.just-os.org/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: userMessage,
      chat_id: chatId,
      session_id: sessionId
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    
    const text = decoder.decode(value);
    const lines = text.split('\n').filter(line => line.trim());
    
    for (const line of lines) {
      const data = JSON.parse(line);
      if (data.status === 'complete') {
        // Display the final response
        console.log(data.message);
      } else {
        // Show processing status
        console.log('Status:', data.message);
      }
    }
  }
}
```

### Adding New Origins

To allow additional domains to access the API, add them to the `ALLOWED_ORIGINS` list in `config/settings.py`:

```python
"ALLOWED_ORIGINS": ["https://forrt.org", "https://example.com"],
```

## Acknowledgements
The development of the application benefitted greatly from the following open source software and public resources:
- Allen Institue for AI's [OpenScholar model](https://huggingface.co/OpenSciLM/Llama-3.1_OpenScholar-8B) and [associated software](https://github.com/AkariAsai/OpenScholar)
- Sebastian Mathot's [Sigmund repository](https://github.com/open-cogsci/sigmund-ai) (The front-end portion of JUST-OS was developed with substantial reference to Sigmund and is hence shared under GPL3)
- The [Unpaywall API](https://unpaywall.org/products/api)
- [This](https://github.com/nickjj/docker-flask-example) example Docker + Flask web app
