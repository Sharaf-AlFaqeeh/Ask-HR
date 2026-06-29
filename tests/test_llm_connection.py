import httpx
import time

def check_services():
    services = {
        "LLM Inference Service": "http://127.0.0.1:8000/health",
        "LLM Inference V1": "http://127.0.0.1:8000/v1/models",
        "Orchestrator Service": "http://127.0.0.1:8081/health",
        "Frontend Service": "http://127.0.0.1:8082"
    }
    
    for name, url in services.items():
        print(f"Checking {name} at {url}...")
        start = time.time()
        try:
            response = httpx.get(url, timeout=3.0)
            duration = time.time() - start
            print(f"  -> SUCCESS! Status: {response.status_code}, Time: {duration:.2f}s")
            try:
                print(f"     Response: {response.text[:100]}...")
            except:
                pass
        except Exception as e:
            print(f"  -> FAILED! Error: {e}")
        print("-" * 50)

if __name__ == "__main__":
    check_services()
