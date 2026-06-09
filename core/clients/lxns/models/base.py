from pydantic import BaseModel


class APIResult(BaseModel):
    success: bool
    code: int
    message: str | None = ""
    data: dict | list | None = None
