from fastapi import FastAPI
import uvicorn
from pathlib import Path

from backend.api.modules.mcp.server import mcp
from backend.api.server.lifespan import lifespan
from backend.api.modules.auth.middleware import bearer_auth
from backend.api.modules.auth.routers import router as oauth_router

app = FastAPI(lifespan=lifespan)
app.middleware("http")(bearer_auth)
app.mount("/mcp", mcp.streamable_http_app(streamable_http_path="/"))
app.include_router(oauth_router)


def main():
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
