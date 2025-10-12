from dotenv import load_dotenv
import os
import sys
import json
import requests
from typing import Dict, Any, List, Tuple

load_dotenv()

BASE_URL = os.getenv("NEBUL_BASE_URL", "https://api.chat.nebul.io/v1")
API_KEY = os.getenv("NEBUL_API_KEY")
CHAT_PATH_STYLE = os.getenv("NEBUL_CHAT_PATH_STYLE", "").strip().lower()
EMBED_PATH_STYLE = os.getenv("NEBUL_EMBED_PATH_STYLE", "").strip().lower()

def _auth_header() -> Dict[str, str]:
    """Builds the HTTP authorization header."""
    if not API_KEY:
        raise RuntimeError("Missing NEBUL_API_KEY environment variable")
    return {"Authorization": f"Bearer {API_KEY}"}

def _bases_to_try() -> List[str]:
    """Returns a list of base URLs to try, toggling presence of /v1."""
    bases = []
    b = BASE_URL.rstrip("/")
    bases.append(b)
    if b.endswith("/v1"):
        bases.append(b[:-3] or b)  # strip /v1
    else:
        bases.append(b + "/v1")
    dedup = []
    for x in bases:
        if x not in dedup:
            dedup.append(x)
    return dedup

def list_models() -> List[Dict[str, Any]]:
    """Lists available models from the OpenAI-compatible /models endpoint."""
    last_err = None
    for base in _bases_to_try():
        try:
            r = requests.get(f"{base}/models", headers=_auth_header(), timeout=30)
            r.raise_for_status()
            data = r.json()
            models = data.get("data", data)
            print(json.dumps(models, indent=2))
            return models
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"/models failed across bases. Last error: {last_err}")

def _try_requests(attempts: List[Tuple[str, str, Dict[str, Any]]]) -> Tuple[str, str, Dict[str, Any]]:
    """Tries a list of (style, path, payload) across candidate base URLs."""
    errors = []
    headers = {**_auth_header(), "Content-Type": "application/json"}
    for base in _bases_to_try():
        for style, path, payload in attempts:
            url = f"{base}{path}"
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=60)
                if 200 <= r.status_code < 300:
                    resp = r.json()
                    print(json.dumps({"used_base": base, "used_path": path, "style": style, "status": r.status_code}, indent=2))
                    return base, path, resp
                errors.append((url, r.status_code, r.text[:500]))
            except requests.RequestException as rexc:
                errors.append((url, "request_error", str(rexc)))
    msg = {"attempts": [{"url": u, "status": s, "body_or_error": t} for (u, s, t) in errors]}
    raise RuntimeError(json.dumps(msg, indent=2))

def chat_example(model: str, user_message: str) -> Dict[str, Any]:
    """Runs a Chat Completions call, trying standard and deployment-style paths."""
    payload_std = {"model": model, "messages": [{"role": "user", "content": user_message}]}
    payload_dep = {"messages": [{"role": "user", "content": user_message}]}
    attempts_all = [
        ("standard", "/chat/completions", payload_std),
        ("deployment", f"/openai/deployments/{model}/chat/completions", payload_dep),
    ]
    if CHAT_PATH_STYLE == "standard":
        attempts = [attempts_all[0], attempts_all[1]]
    elif CHAT_PATH_STYLE == "deployment":
        attempts = [attempts_all[1], attempts_all[0]]
    else:
        attempts = attempts_all
    _, _, resp = _try_requests(attempts)
    choices = resp.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content") or choices[0].get("text", "")
        print(json.dumps({"chat_preview": (content[:200] if content else "")}, indent=2))
    return resp

def embed_example(model: str, text: str) -> Dict[str, Any]:
    """Runs an Embeddings call, trying standard and deployment-style paths."""
    payload_std = {"model": model, "input": text}
    payload_dep = {"input": text}
    attempts_all = [
        ("standard", "/embeddings", payload_std),
        ("deployment", f"/openai/deployments/{model}/embeddings", payload_dep),
    ]
    if EMBED_PATH_STYLE == "standard":
        attempts = [attempts_all[0], attempts_all[1]]
    elif EMBED_PATH_STYLE == "deployment":
        attempts = [attempts_all[1], attempts_all[0]]
    else:
        attempts = attempts_all
    _, _, resp = _try_requests(attempts)
    data = resp.get("data", [])
    summary = {}
    if isinstance(data, list) and data:
        first = data[0]
        emb = first.get("embedding")
        dims = len(emb) if isinstance(emb, list) else None
        summary = {"embeddings": {"count": len(data), "dimensions": dims}}
    else:
        summary = {"embeddings": {"count": 0, "dimensions": None}}
    print(json.dumps(summary, indent=2))
    return resp

def main() -> None:
    """Lists models; if names provided, runs one chat and one embeddings call with auto-fallback."""
    models = list_models()
    if len(sys.argv) >= 3:
        chat_model = sys.argv[1]
        embed_model = sys.argv[2]
        chat_example(chat_model, "Say hello and tell me your model id.")
        embed_example(embed_model, "Amsterdam is the capital of the Netherlands.")
    else:
        print("\nUsage: python test_nebul.py <chat_model_id> <embed_model_id>")
        print("Env toggles: NEBUL_CHAT_PATH_STYLE=standard|deployment, NEBUL_EMBED_PATH_STYLE=standard|deployment")
        print("BASES tried: current NEBUL_BASE_URL and variant with/without /v1.")

if __name__ == "__main__":
    main()