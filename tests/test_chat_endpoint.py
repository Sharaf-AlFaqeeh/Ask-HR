import httpx

def main():
    url = "http://127.0.0.1:8081/api/v1/chat"
    headers = {
        "Authorization": "Bearer askhr_super_secret_token_2026",
        "Content-Type": "application/json"
    }
    payload = {
        "query": "ما هي سياسة الإجازة السنوية؟"
    }
    
    print(f"Sending request to {url}...")
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        import json
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    main()
