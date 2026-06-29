import json
import sys

def main():
    log_path = "logs/app.log"
    out_path = "tests/search_app_log_results.txt"
    print(f"Reading {log_path} and writing results to {out_path}...")
    
    # Force output file to use utf-8
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f, \
         open(out_path, "w", encoding="utf-8") as out:
        for line in f:
            try:
                data = json.loads(line)
                message = data.get("message", "")
                if any(x in message for x in ["مخططة", "15", "01", "5553"]):
                    out.write(f"[{data.get('timestamp')}] [{data.get('logger')}] {message}\n")
            except Exception as e:
                if any(x in line for x in ["مخططة", "15", "01", "5553"]):
                    out.write(line)

if __name__ == "__main__":
    main()
