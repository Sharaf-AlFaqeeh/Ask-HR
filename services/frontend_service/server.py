import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(
    title="AskHR Portal Service",
    description="Lightweight static portal service for AskHR Enterprise UI",
    version="1.1.0"
)

# Get absolute path of current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Serve index.html at root
@app.get("/")
def read_root():
    index_path = os.path.join(current_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return "<h1>AskHR Portal is starting... Please refresh soon.</h1>", 200

# Mount all other static files (CSS, JS, images, etc.)
app.mount("/", StaticFiles(directory=current_dir), name="static")

if __name__ == "__main__":
    # The frontend runs by default on port 8082
    port = int(os.getenv("PORT", 8082))
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=True)
