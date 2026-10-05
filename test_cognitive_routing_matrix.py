import json
import os
import time

import requests

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


def extract_mode_from_stream(message: str) -> str:
    payload = {
        "message": message,
        "history": [],
        "session_id": "matrix_test",
        "model": "openrouter/free",
    }

    response = requests.post(f"{BASE_URL}/chat/tools", json=payload, stream=True, timeout=180)
    response.raise_for_status()

    for line in response.iter_lines():
        if not line:
            continue

        line_str = line.decode("utf-8")
        if not line_str.startswith("data: "):
            continue

        data_content = line_str[6:]
        if data_content == "[DONE]":
            break

        try:
            data = json.loads(data_content)
        except json.JSONDecodeError:
            continue

        if data.get("type") == "info":
            message_text = data.get("message", "")
            if "Mode:" in message_text:
                return message_text.split("Mode:", 1)[1].split("|", 1)[0].strip()

    return "unknown"


def run_matrix() -> int:
    matrix = [
        {
            "query": "Kapan Indonesia merdeka?",
            "expected": ["direct_factual_mode", "factual_mode"],
        },
        {
            "query": "Leads banyak tapi closing rendah. Tolong bantu diagnosis.",
            "expected": ["operational_bottleneck_mode", "diagnosis_first_mode"],
        },
        {
            "query": "Saya ingin mengubah tacit knowledge CEO menjadi explicit knowledge organisasi.",
            "expected": ["governance_analysis_mode", "strategic_facilitation_mode"],
        },
        {
            "query": "Bagaimana membuat observability dashboard marketing untuk lintas funnel?",
            "expected": ["systems_thinking_mode", "operational_bottleneck_mode"],
        },
        {
            "query": "Jelaskan quantum computing seperti umur 5 tahun",
            "expected": ["educational_mode", "direct_factual_mode"],
        },
    ]

    passed = 0
    for i, item in enumerate(matrix, start=1):
        mode = extract_mode_from_stream(item["query"])
        ok = mode in item["expected"]
        if ok:
            passed += 1

        print(f"[{i}] mode={mode} | expected={item['expected']} | pass={ok}")

    print(f"\nResult: {passed}/{len(matrix)} passed")
    return 0 if passed == len(matrix) else 1


if __name__ == "__main__":
    for _ in range(10):
        try:
            health = requests.get(f"{BASE_URL}/health", timeout=3)
            if health.status_code == 200:
                break
        except requests.RequestException:
            time.sleep(1)

    raise SystemExit(run_matrix())
