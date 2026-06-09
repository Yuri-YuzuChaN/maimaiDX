from pydantic import BaseModel

from .collection import Collection


class Player(BaseModel):
    name: str
    rating: int
    friend_code: int
    course_rank: int
    class_rank: int
    star: int
    trophy: Collection | None = None
    icon: Collection | None = None
    name_plate: Collection | None = None
    frame: Collection | None = None
    upload_time: str | None = None
