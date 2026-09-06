from contextlib import asynccontextmanager
from fastapi import FastAPI

from backend.api.modules.mcp.server import mcp
from backend.api.modules.auth.store import DynamoDBAuthStore

auth_store = DynamoDBAuthStore()


# lifespan -> mcp's session manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    await auth_store.ensure_table()

    async with mcp.session_manager.run():
        yield
