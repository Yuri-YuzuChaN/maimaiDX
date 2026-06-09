from pydantic import BaseModel

from .enum import StatusEnum
from .status import AliasStatus


class Alias(BaseModel):
    song_id: int
    name: str
    is_votable: bool
    alias: list[str]


class Songs(BaseModel):
    type: StatusEnum
    data: list[Alias] | list[AliasStatus]
