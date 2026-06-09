from pydantic import BaseModel


class BaseToken(BaseModel):
    access_token: str
    refresh_token: str


class OAuth2Token(BaseToken):
    token_type: str
    expires_in: int
    scope: str
