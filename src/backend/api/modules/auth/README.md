 # OAuth authentication

This package contains a small, educational OAuth 2.0 authorization-code flow
for the MCP server. It is designed to make the protocol understandable. It is
not production-ready: clients, authorization codes, and access tokens are
currently stored in memory, and the approval page is a fake login/consent step.

## The architecture

There are three roles:

```text
Inspector (client)
        │ obtains an access token
        ▼
OAuth endpoints (authorization server)
        │ issues the access token
        ▼
MCP endpoint (resource server)
        │ validates the access token
        ▼
Tools and resources
```

The roles can live in the same FastAPI process during development. They are
conceptually separate:

- **Client**: an application requesting access. Here, MCP Inspector is the
  client.
- **Authorization server**: authenticates a user, obtains consent, and issues
  tokens. The `/oauth/*` routes play this role in this demo.
- **Resource server**: hosts protected data or operations and validates access
  tokens. The `/mcp` route plays this role.
- **Access token**: a credential sent with requests to the resource server.
- **Bearer token**: a token that grants access to whoever possesses it. It is
  sent as `Authorization: Bearer <token>`.

## Files and responsibilities

```text
auth/
├── middleware.py   Checks bearer access tokens on /mcp requests
├── models.py       Pydantic request models and stored-data structures
├── controllers.py  OAuth state and business logic
├── routers.py      HTTP routes and request parsing
└── README.md       This explanation
```

`main.py` registers the middleware and includes the router. The MCP server is
mounted separately at `/mcp`.

## Discovery with `.well-known`

`.well-known` is a standard URL location for machine-readable server
configuration. An OAuth client can discover the authentication endpoints
instead of having them hard-coded.

### Protected-resource metadata

```text
GET /.well-known/oauth-protected-resource/mcp
```

This describes the protected MCP resource and identifies its authorization
server.

### Authorization-server metadata

```text
GET /.well-known/oauth-authorization-server
```

This tells the client where to find:

- the authorization endpoint: `/oauth/authorize`
- the token endpoint: `/oauth/token`
- the registration endpoint: `/oauth/register`
- supported flow: `authorization_code`
- supported PKCE method: `S256`

## Complete authorization-code flow

### 1. Client registration

Inspector registers itself:

```text
POST /oauth/register
Content-Type: application/json
```

Example request:

```json
{
  "client_name": "MCP Inspector",
  "redirect_uris": [
    "http://localhost:6274/oauth/callback"
  ]
}
```

The server creates a `client_id` and stores the client in `clients` in
`controllers.py`.

### 2. PKCE preparation

Before authorization, the client creates a random secret called the
**code verifier**. It hashes that secret to create a **code challenge**.

```text
code_verifier  = random secret
code_challenge = BASE64URL(SHA256(code_verifier))
```

The client sends only the challenge initially. It keeps the verifier private
until the token exchange.

**PKCE** (Proof Key for Code Exchange, pronounced “pixy”) prevents somebody who
intercepts an authorization code from exchanging it without also knowing the
original verifier.

### 3. Authorization request

The client opens a browser URL:

```text
GET /oauth/authorize?
    client_id=...
    &redirect_uri=...
    &response_type=code
    &scope=workspace:read+workspace:write
    &state=...
    &code_challenge=...
    &code_challenge_method=S256
```

`routers.py` reads these query parameters through `Depends()` and creates an
`AuthorizationRequest` model.

The controller verifies that:

- the client exists;
- `response_type` is `code`;
- the PKCE method is `S256`; and
- the redirect URI exactly matches one registered by the client.

### 4. User approval

The server returns an HTML approval page. In this demo, clicking the button is
the entire approval step; there is no real user login yet.

The form submits to:

```text
POST /oauth/authorize/approve
```

Because this is an HTML form, `routers.py` reads its values using `Form(...)`.

### 5. Authorization code

After approval, the server creates a short-lived authorization code and stores:

```text
client_id
redirect_uri
code_challenge
scope
expires_at
```

The browser is redirected to the registered callback/redirect URI:

```text
http://localhost:6274/oauth/callback?code=...&state=...
```

The **redirect URI** is the client URL where the authorization server returns
the browser after approval. The **callback** is the code at that URL that
receives the returned code.

The `state` value is created and checked by the client. It helps the client
make sure the response belongs to the authorization request it started.

### 6. Token exchange

The client sends the authorization code and its original PKCE verifier:

```text
POST /oauth/token
Content-Type: application/x-www-form-urlencoded
```

```text
grant_type=authorization_code
code=...
redirect_uri=...
client_id=...
code_verifier=...
```

The server validates:

- the grant type;
- the client;
- the code;
- code expiration;
- the client associated with the code;
- the redirect URI; and
- the PKCE verifier.

If valid, the server deletes the authorization code so it cannot be reused and
returns an access token:

```json
{
  "access_token": "...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "workspace:read workspace:write"
}
```

### 7. Calling MCP

The client calls the MCP endpoint with:

```http
Authorization: Bearer <access_token>
```

`bearer_auth` in `middleware.py` extracts the token, looks it up in
`access_tokens`, checks its expiry, and forwards valid requests to MCP using
`call_next(request)`.

Invalid, missing, or expired tokens receive `401 Unauthorized`.

## Important terminology

| Term | Meaning in this project |
| --- | --- |
| Client | Inspector, the application requesting MCP access |
| Client ID | Public identifier assigned during registration |
| Redirect URI | Registered URL where the client receives the authorization code |
| Callback | The client code listening at the redirect URI |
| Authorization code | Short-lived, one-time code exchanged for an access token |
| Access token | Credential used to call `/mcp` |
| Scope | Named permission, such as `workspace:read` |
| PKCE verifier | Secret kept by the client during the flow |
| PKCE challenge | Hash of the verifier sent during authorization |
| State | Client-generated value used to correlate request and response |
| Bearer token | Token accepted from whoever possesses it |
| Resource server | The protected MCP server |
| Authorization server | The server issuing OAuth tokens |

## Current limitations

This implementation is intentionally simplified:

- all OAuth state is lost when the process restarts;
- the approval page does not authenticate a real user;
- tokens are opaque random strings rather than signed JWTs;
- scopes are recorded but not yet enforced per tool/resource;
- there are no refresh or revocation endpoints;
- the debug-style in-memory stores are not suitable for multiple workers; and
- production use would require HTTPS, secure sessions, real user authentication,
  persistent storage, rate limiting, and stronger validation.

The next practical step is moving `clients`, `authorization_codes`, and
`access_tokens` into a database. Real user authentication and scope enforcement
can then be added on top of this flow.
