from pydantic import BaseModel


class StatusBase(BaseModel):
    song_id: int
    apply_uid: int | str
    apply_alias: str


class Approved(StatusBase):
    tag: str
    name: str
    group_id: int | None = None
    ws_uuid: str | None = None


class AliasStatus(StatusBase):
    tag: str
    name: str
    created_at: str
    agree_votes: int | None = 0
    votes: int


class Reviewed(StatusBase):
    tag: str
    name: str


class PushAliasStatus(BaseModel):
    type: str
    status: list[AliasStatus] | list[Approved] | list[Reviewed]
