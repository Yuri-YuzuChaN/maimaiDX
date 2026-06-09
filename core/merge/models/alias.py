from pydantic import BaseModel


class Alias(BaseModel):
    song_id: int
    song_name: str
    alias: list[str]


class AliasesPush(BaseModel):
    enable: list[int] = []
    disable: list[int] = []
