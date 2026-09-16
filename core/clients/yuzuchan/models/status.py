from pydantic import BaseModel


class AliasStatus(BaseModel):
    song_id: int
    apply_alias: str
    tag: str
    name: str
    created_at: str
    agree_votes: int | None = 0
    votes: int


class PushAliasStatus(BaseModel):
    type: str
    status: list[AliasStatus]
