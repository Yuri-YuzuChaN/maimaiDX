import re
from urllib.parse import parse_qs, urlencode, urlparse

AUTHORIZATION_CODE_PATTERN = re.compile(
    r"^(?:[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}"
    r"|[A-Za-z0-9_-]{16,256})$"
)


def build_authorize_url(client_id: str, redirect_uri: str) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "read_player read_user_profile write_player",
        }
    )
    return f"https://maimai.lxns.net/oauth/authorize?{query}"


def is_binding_channel_allowed(*, private_only: bool, is_private: bool) -> bool:
    return is_private or not private_only


def extract_authorization_code(text: str) -> str | None:
    value = text.strip()
    if AUTHORIZATION_CODE_PATTERN.fullmatch(value):
        return value

    prefixed = re.fullmatch(r"授权码\s*[:：]?\s*(\S+)", value)
    if prefixed:
        code = prefixed.group(1)
        if AUTHORIZATION_CODE_PATTERN.fullmatch(code):
            return code

    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        code = parse_qs(parsed.query).get("code", [None])[0]
        if code and AUTHORIZATION_CODE_PATTERN.fullmatch(code):
            return code

    return None
