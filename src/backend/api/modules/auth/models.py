from pydantic import BaseModel, Field
from dataclasses import dataclass


class ClientRegistrationRequest(BaseModel):
    client_name: str | None = None
    redirect_uris: list[str] = Field(default_factory=list)
    grant_types: list[str] = Field(default_factory=lambda: ["authorization_code"])
    response_types: list[str] = Field(default_factory=lambda: ["code"])


@dataclass
class AuthorizationCode:
    client_id: str
    redirect_uri: str
    code_challenge: str
    scope: str
    expires_at: float


class AuthorizationRequest(BaseModel):
    client_id: str
    redirect_uri: str
    response_type: str
    scope: str = ""
    state: str | None = None
    code_challenge: str
    code_challenge_method: str


@dataclass
class AccessToken:
    client_id: str
    scope: str
    expires_at: float
