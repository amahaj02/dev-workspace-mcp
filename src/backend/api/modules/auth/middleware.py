from fastapi import Request
from fastapi.responses import JSONResponse
import time

from backend.api.modules.auth.store import DynamoDBAuthStore

store = DynamoDBAuthStore()


# middleware for ensuring request is accompanied with correct token
# call_next means once the token is validated, continue processing
# the request and send it to the next route
async def bearer_auth(request: Request, call_next):
    metadata_url = "http://127.0.0.1:8000/" ".well-known/oauth-protected-resource/mcp"
    if request.url.path.rstrip("/") == "/mcp":
        authorization = request.headers.get("authorization", "")
        token = authorization.removeprefix("Bearer ").strip()
        access_token = await store.get_access_token(token)

        if access_token is None or access_token["expires_at"] < time.time():
            return JSONResponse(
                {"error": "Unauthorized"},
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{metadata_url}"'
                },
            )
    return await call_next(request)
