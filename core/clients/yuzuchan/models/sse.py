from pydantic import BaseModel


class SSEMessage(BaseModel):
    event: str
    data: str
    id: str | None = None
    retry: int | None = None
