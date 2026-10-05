"""Optional provider connectivity check; never logs secret material."""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()


def test_openrouter() -> int:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY is not configured; provider check skipped")
        return 0

    payload = {
        "model": os.getenv("OPENROUTER_MODEL", "openrouter/free"),
        "messages": [{"role": "user", "content": "Hello, are you working?"}],
        "max_tokens": 50,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost:5008"),
        "X-Title": "Nexus AI Test",
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30,
        )
        print(f"Status Code: {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2)[:2_000])
        except ValueError:
            print(response.text[:500])
        return 0 if response.ok else 1
    except requests.RequestException as exc:
        print(f"Provider check failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(test_openrouter())
