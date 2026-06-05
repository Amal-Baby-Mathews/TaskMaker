# OpenAI-Compatible Local Inference API

An OpenAI-compatible server running on a local or remote network inference host.
This document explains how to reach the inference endpoint from your local machine and call it using typical HTTP and client SDK patterns.

| | |
|---|---|
| **Model served** | Configured model ID (e.g. specified in `config.json`) |
| **Listen address** | Local port or forwarded network port (e.g. `localhost:9999`) |
| **API style** | OpenAI-compatible (`/v1/...`) |
| **Auth** | Typically none (unless API key specified in client setup) |

---

## 1. Connect via SSH Port Forwarding (If applicable)

If the server is bound to a remote loopback or private host address, forward a local port on your machine to it:

```bash
# Forward YOUR localhost:9999  ->  Remote Host's localhost:9999
ssh -N -L 9999:localhost:9999 your-ssh-host-name
```

*   `-N` = do not open an interactive shell session.
*   `-L 9999:localhost:9999` = bind local port `9999` to remote host's `9999` port.
*   Keep this command running in the background or in a separate terminal tab.

Once the tunnel is active, the base endpoint URL is:
```
http://localhost:9999
```

### Quick Sanity Check
```bash
curl http://localhost:9999/health        # -> 200 OK (empty body)
curl http://localhost:9999/v1/models      # -> JSON listing of available models
```

---

## 2. Endpoints

Base URL: `http://localhost:9999`

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/chat/completions` | **Main endpoint.** Chat-style generation (system/user/assistant messages). |
| `POST` | `/v1/completions` | Raw text completion. |
| `GET`  | `/v1/models` | List served models and metadata. |
| `GET`  | `/health` | Liveness check. |

---

## 3. Usage Examples

Replace `your-model-name` in the payload with the target model ID (as configured in `config.json`).

### 3a. Chat Completion — curl
```bash
curl http://localhost:9999/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain SSH port forwarding in two sentences."}
    ],
    "max_tokens": 256,
    "temperature": 0.7
  }'
```

### 3b. Streaming (SSE)
```bash
curl http://localhost:9999/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "messages": [{"role": "user", "content": "Write a haiku about GPUs."}],
    "stream": true
  }'
```

### 3c. Python — OpenAI SDK
```python
from openai import OpenAI

# Point the OpenAI client at the endpoint.
client = OpenAI(base_url="http://localhost:9999/v1", api_key="not-needed")

resp = client.chat.completions.create(
    model="your-model-name",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Give me 3 uses for an edge LLM."},
    ],
    max_tokens=300,
    temperature=0.7,
)
print(resp.choices[0].message.content)
```

---

## 4. Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `Failed to connect to localhost port 9999` | SSH tunnel isn't running or local endpoint is down. Check connection settings. |
| `bind: Address already in use` on tunnel start | Local port 9999 is taken by another application. Bind to a different port, e.g. `-L 8080:localhost:9999`. |
| `404 model not found` | Ensure that the `"model"` key in your request matches exactly one of the model IDs returned by `GET /v1/models`. |
