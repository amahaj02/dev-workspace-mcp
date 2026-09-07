from contextlib import asynccontextmanager
from fastapi import FastAPI

from backend.api.modules.mcp.server import mcp


# lifespan -> mcp's session manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield
