import os
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(
    title="AskHR Portal Service",
    description="Lightweight static portal service for AskHR Enterprise UI",
    version="1.2.0"
)

# Add middleware to disable caching for static assets during active development
@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Get absolute path of current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
dist_dir = os.path.join(current_dir, "dist")

# Serve index.html at root
@app.get("/")
def read_root():
    index_path = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return "<h1>AskHR Portal: Please run 'npm run build' or start Vite dev server on port 8082.</h1>", 200

# Mount static files (assets, etc.)
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir), name="static")
else:
    app.mount("/", StaticFiles(directory=current_dir), name="static")

if __name__ == "__main__":
    # The frontend runs by default on port 8082
    port = int(os.getenv("PORT", 8082))
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=True)

