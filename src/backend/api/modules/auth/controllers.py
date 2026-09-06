import secrets
import time
from urllib.parse import urlencode
import base64
import hashlib

from fastapi.responses import RedirectResponse
from fastapi import HTTPException


from backend.api.modules.auth.models import (
    AuthorizationRequest,
)

from backend.api.modules.auth.store import DynamoDBAuthStore

store = DynamoDBAuthStore()


async def register_client(client_data: dict) -> dict:
    client_id = secrets.token_urlsafe(16)

    client = {
        "client_id": client_id,
        "client_name": client_data.get("client_name", "Unknown client"),
        "redirect_uris": client_data.get("redirect_uris", []),
        "grant_types": client_data.get(
            "grant_types",
            ["authorization_code"],
        ),
        "response_types": client_data.get(
            "response_types",
            ["code"],
        ),
        "token_endpoint_auth_method": "none",
        "client_id_issued_at": int(time.time()),
    }

    await store.put_client(client)
    return client


async def create_authorization_code(
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    scope: str,
) -> str:
    code = secrets.token_urlsafe(32)

    await store.put_authorization_code(
        code,
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "scope": scope,
            "expires_at": time.time() + 300,
        },
    )

    return code


async def authorize(request: AuthorizationRequest):
    client = await store.get_client(request.client_id)
    if client is None:
        raise HTTPException(
            status_code=400,
            detail="Unknown client_id",
        )

    if request.response_type != "code":
        raise HTTPException(
            status_code=400,
            detail="Only response_type=code is supported",
        )

    if request.code_challenge_method != "S256":
        raise HTTPException(
            status_code=400, detail="Only code_challenge_method=S256 is supported"
        )

    if request.redirect_uri not in client["redirect_uris"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid redirect_uri",
        )

    return f"""
    <!doctype html>
    <html>
        <head>
            <title>Authorize MCP Client</title>
        </head>
        <body>
            <h1>Authorize application</h1>

            <p>
                <strong>{client["client_name"]}</strong>
                wants to access your workspace.
            </p>

            <p>Requested scopes: {request.scope or "none"}</p>

            <form method="post" action="/oauth/authorize/approve">
                <input type="hidden" name="client_id"
                       value="{request.client_id}">
                <input type="hidden" name="redirect_uri"
                       value="{request.redirect_uri}">
                <input type="hidden" name="scope"
                       value="{request.scope}">
                <input type="hidden" name="state"
                       value="{request.state or ""}">
                <input type="hidden" name="code_challenge"
                       value="{request.code_challenge}">

                <button type="submit">
                    Approve access
                </button>
            </form>
        </body>
    </html>
    """


async def approve_oauth_authorization(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
):
    client = await store.get_client(client_id)
    if client is None:
        raise HTTPException(
            status_code=400,
            detail="Unknown client_id",
        )
    if redirect_uri not in client["redirect_uris"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid redirect_uri",
        )
    code = await create_authorization_code(
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        scope=scope,
    )

    redirect_parameters = {
        "code": code,
    }

    if state:
        redirect_parameters["state"] = state

    separator = "&" if "?" in redirect_uri else "?"

    redirect_url = redirect_uri + separator + urlencode(redirect_parameters)

    return RedirectResponse(url=redirect_url, status_code=303)


async def exchange_authorization_code(
    grant_type: str,
    code: str,
    redirect_uri: str,
    client_id: str,
    code_verifier: str,
) -> dict:
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="Unsupported grant_type")

    client = await store.get_client(client_id)

    if client is None:
        raise HTTPException(status_code=400, detail="Unknown client_id")

    authorization_code = await store.get_authorization_code(code)

    if authorization_code is None:
        raise HTTPException(status_code=400, detail="Invalid authorization code")

    if authorization_code["expires_at"] < time.time():
        await store.consume_authorization_code(code)
        raise HTTPException(status_code=400, detail="Authorization code expired")

    if authorization_code["client_id"] != client_id:
        raise HTTPException(
            status_code=400, detail="Authorization code belongs to another client"
        )
    if authorization_code["redirect_uri"] != redirect_uri:
        raise HTTPException(status_code=400, detail="Redirect URI does not match")

    expected_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )

    if not secrets.compare_digest(
        expected_challenge, authorization_code["code_challenge"]
    ):
        raise HTTPException(status_code=400, detail="Invalid PKCE identifier")
    if not await store.consume_authorization_code(code):
        raise HTTPException(status_code=400, detail="Authorization code already in use")

    access_token = secrets.token_urlsafe(32)
    expires_in = 3600

    await store.put_access_token(
        access_token,
        {
            "client_id": client_id,
            "scope": authorization_code["scope"],
            "expires_at": time.time() + expires_in,
        },
    )

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": authorization_code["scope"],
    }
