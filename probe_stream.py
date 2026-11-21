import json
import urllib.request

api_key = input("Paste Velona API key (or Enter to use env): ").strip()
model_id = input("Paste model ID (e.g. deepseek/deepseek-v4-flash-0731): ").strip()

payload = {
    "api_base": "https://velona.in/gateway/v1/inference/run",
    "api_key": api_key,
    "model": model_id,
    "prompt": "Reply with a one-line status check: OK",
}

req = urllib.request.Request(
    "http://127.0.0.1:8080/api/analyze-stream",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req, timeout=60) as resp:
    for raw in resp:
        line = raw.decode("utf-8", errors="replace").strip()
        if line:
            print(line[:300])
