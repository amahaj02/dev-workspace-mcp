from fastapi import APIRouter, Form, Depends
from fastapi.responses import HTMLResponse

from backend.api.modules.auth.models import (
    ClientRegistrationRequest,
    AuthorizationRequest,
)

from backend.api.modules.auth.controllers import (
    register_client,
    authorize,
    approve_oauth_authorization,
    exchange_authorization_code,
)

router = APIRouter()

ISSUER = "http://127.0.0.1:8000"
MCP_RESOURCE = f"{ISSUER}/mcp"


@router.get("/.well-known/oauth-protected-resource/mcp")
async def protected_resource_metadata():
    return {
        "resource": MCP_RESOURCE,
        "authorization_servers": [ISSUER],
        "scopes_supported": [
            "workspace:read",
            "workspace:write",
        ],
        "bearer_methods_supported": ["header"],
    }


@router.get("/.well-known/oauth-authorization-server")
async def authorization_server_metadata():
    return {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/oauth/authorize",
        "token_endpoint": f"{ISSUER}/oauth/token",
        "registration_endpoint": f"{ISSUER}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
    }


@router.post("/oauth/register")
async def register_oauth_client(
    request: ClientRegistrationRequest,
):
    return await register_client(request.model_dump())


@router.get("/oauth/authorize", response_class=HTMLResponse)
async def authorize_oauth_client(request: AuthorizationRequest = Depends()):
    return await authorize(request)


@router.post("/oauth/authorize/approve")
async def approve_oauth_client(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(""),
    state: str = Form(""),
    code_challenge: str = Form(...),
):
    return await approve_oauth_authorization(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
    )


@router.post("/oauth/token")
async def oauth_token(
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    code_verifier: str = Form(...),
):
    return await exchange_authorization_code(
        grant_type=grant_type,
        code=code,
        redirect_uri=redirect_uri,
        client_id=client_id,
        code_verifier=code_verifier,
    )
