from pydantic import BaseModel, ConfigDict, Field


class RecordsQueryRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )

    song_id: int | None = Field(None)
    level: str | None = Field(None)
    level_index: int | None = Field(None)
    level_value: float | None = Field(None, serialization_alias="ds")
    fullcombo: str | list[str] | None = Field(None, serialization_alias="fc")
    fullsync: str | list[str] | None = Field(None, serialization_alias="fs")
    plate: str | None = Field(None)
    version: list[str] | None = Field(None)
