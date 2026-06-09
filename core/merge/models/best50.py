from pydantic import BaseModel

from .score import PlayedResult


class Best50(BaseModel):
    sd_total: int
    dx_total: int
    sd: list[PlayedResult] = []
    dx: list[PlayedResult] = []
