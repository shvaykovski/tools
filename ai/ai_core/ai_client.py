import json
import urllib.request
import urllib.error
import sys
from .config import (
    OPENAI_KEY,
    ANTHROPIC_KEY,
    OPENROUTER_KEY,
    GOOGLE_KEY,
    OLLAMA_URL,
    ANTHROPIC_URL,
    OPENROUTER_URL,
    OPENAI_URL,
    GOOGLE_URL,
)
from .colors import RED, RESET


def call_ai(messages, provider, model, temperature=0.1, max_tokens=2048, timeout=90):
    """Generic wrapper for various AI providers using urllib."""
    headers = {"Content-Type": "application/json"}

    if provider == "anthropic":
        url = ANTHROPIC_URL
        headers.update({"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"})
        system_msg = messages[0]["content"] if messages[0]["role"] == "system" else ""
        user_msgs = [m for m in messages if m["role"] != "system"]
        data = {
            "model": model,
            "system": system_msg,
            "messages": user_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    elif provider == "openrouter":
        url = OPENROUTER_URL
        headers.update(
            {
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "HTTP-Referer": "https://google.com/",
                "X-Title": "AI Tools Suite",
            }
        )
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    elif provider == "openai":
        url = OPENAI_URL
        headers["Authorization"] = f"Bearer {OPENAI_KEY}"
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    elif provider == "google":
        url = f"{GOOGLE_URL}/{model}:generateContent"
        headers["x-goog-api-key"] = GOOGLE_KEY

        system_msg = next(
            (m["content"] for m in messages if m["role"] == "system"), None
        )
        user_msgs = [
            {
                "role": "user" if m["role"] == "user" else "model",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
            if m["role"] != "system"
        ]

        data = {
            "contents": user_msgs,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_msg:
            data["systemInstruction"] = {"parts": [{"text": system_msg}]}
    else:  # Default to Ollama
        url = f"{OLLAMA_URL}/api/chat"
        data = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode(), headers=headers
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res = json.loads(response.read())
            if provider == "anthropic":
                return res["content"][0]["text"].strip()
            elif provider == "ollama":
                return res["message"]["content"].strip()
            elif provider == "google":
                return res["candidates"][0]["content"]["parts"][0]["text"].strip()
            return res["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        print(f"{RED}API Error: {e.code} - {e.reason}{RESET}", file=sys.stderr)
        try:
            error_details = json.loads(e.read())
            print(
                f"Details: {error_details.get('error', {}).get('message')}",
                file=sys.stderr,
            )
        except:
            pass
        return ""
    except Exception as e:
        print(f"{RED}Error connecting to {url}: {e}{RESET}", file=sys.stderr)
        return ""
