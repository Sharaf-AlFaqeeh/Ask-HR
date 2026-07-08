import os
import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI(
    title="AskHR Portal Service",
    description="Lightweight static portal service for AskHR Enterprise UI",
    version="1.2.0"
)

# Backend Orchestrator URL
ORCHESTRATOR_URL = "http://127.0.0.1:8081"

# Add middleware to disable caching for static assets during active development
@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Proxy health checks to orchestrator backend
@app.get("/health")
async def proxy_health():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{ORCHESTRATOR_URL}/health", timeout=5.0)
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
        except Exception as e:
            return Response(content=f"Error connecting to backend: {str(e)}", status_code=502)

# Asynchronous streaming reverse proxy for API requests
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy_api(request: Request, path: str):
    url = f"{ORCHESTRATOR_URL}/api/{path}"
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    
    client = httpx.AsyncClient()
    req = client.build_request(
        method=request.method,
        url=url,
        headers=headers,
        params=request.query_params,
        content=body
    )
    
    try:
        resp = await client.send(req, stream=True)
        # Filter headers that shouldn't be forwarded
        exclude_headers = ["connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"]
        response_headers = {k: v for k, v in resp.headers.items() if k.lower() not in exclude_headers}
        
        async def generate():
            try:
                async for chunk in resp.aiter_raw():
                    yield chunk
            finally:
                await resp.aclose()
                await client.aclose()
                
        return StreamingResponse(
            generate(),
            status_code=resp.status_code,
            headers=response_headers
        )
    except Exception as e:
        await client.aclose()
        return Response(content=f"Proxy connection failed: {str(e)}", status_code=502)

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

