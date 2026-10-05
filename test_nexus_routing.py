import json
import os
import time

import requests

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

def test_query(message, description):
    print(f"\n--- TEST: {description} ---")
    print(f"Query: {message}")
    
    payload = {
        "message": message,
        "history": [],
        "session_id": "test_session",
        "model": "openrouter/free"
    }
    
    try:
        # Use /chat/tools which has the routing logic
        response = requests.post(f"{BASE_URL}/chat/tools", json=payload, stream=True)
        
        routing_detected = None
        full_text = ""
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    data_content = line_str[6:]
                    if data_content == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_content)
                        if data.get("type") == "info" and "🧠" in data.get("message", ""):
                            routing_detected = data["message"]
                            print(f"Routing Info: {routing_detected}")
                        elif data.get("type") == "text":
                            full_text += data["text"]
                    except:
                        pass
        
        print(f"Response Preview: {full_text[:200]}...")
        return routing_detected, full_text
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def run_smoke_tests():
    # 1. Factual Test
    test_query("Kapan Indonesia merdeka?", "Factual Question")
    
    # 2. Ambiguous Strategic Test (Should trigger Grill-Me or Restraint)
    test_query("Saya ingin jualan kopi tapi belum ada pembeli. Gimana caranya?", "Ambiguous Strategic Marketing")
    
    # 3. Systems/Architecture Test
    test_query("Bagaimana cara membuat sistem microservices yang scalable dengan kubernetes?", "Systems/Architecture")
    
    # 4. Educational Test
    test_query("Jelaskan apa itu quantum computing seperti saya umur 5 tahun", "Educational")

if __name__ == "__main__":
    # Wait for server to be ready
    print("Waiting for Nexus AI backend to be ready...")
    for _ in range(10):
        try:
            resp = requests.get(f"{BASE_URL}/health")
            if resp.status_code == 200:
                print("Server is UP!")
                break
        except:
            time.sleep(2)
    
    run_smoke_tests()
