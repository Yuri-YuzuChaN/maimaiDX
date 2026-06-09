from pydantic import BaseModel


class MessageResult(BaseModel):
    message: str
