from typing import overload

from ..clients.divingfish.models import PlayInfoDefault, PlayInfoDev
from ..clients.lxns.models import Score, SongType
from ..service import mai
from .models import NotPlayedResult, PlayedResult, Song


def df_format_result(
    v: PlayInfoDefault | PlayInfoDev, level_value: float = 0
) -> PlayedResult:
    ds = v.ds if level_value == 0 else level_value
    return PlayedResult(
        song_id=v.song_id,
        song_name=v.title,
        level=v.level,
        level_index=v.level_index,
        level_value=ds,
        type=v.type,
        rating=v.ra,
        achievements=v.achievements,
        fc=v.fc,
        fs=v.fs,
        rate=v.rate,
        dx_score=v.dxScore,
    )


@overload
def df_to_playresult(data: list[Score]) -> list[PlayedResult]: ...
@overload
def df_to_playresult(
    data: list[Score], *, song: Song | None = None
) -> list[PlayedResult | NotPlayedResult]: ...
def df_to_playresult(
    data: list[PlayInfoDefault] | list[PlayInfoDev], *, song: Song | None = None
) -> list[PlayedResult | NotPlayedResult]:
    if song:
        r = [
            NotPlayedResult(
                level_value=v.level_value,
                song_id=song.song_id,
                level_index=v.level_index,
            )
            for v in song.difficulties
        ]
    else:
        r = []

    for v in data:
        if song:
            r[v.level_index] = df_format_result(v, r[v.level_index].level_value)
        else:
            r.append(df_format_result(v))

    return r


def lxns_format_result(v: Score) -> PlayedResult:
    if v.type == SongType.STANDARD:
        song_id = v.id
    elif v.type == SongType.DX:
        song_id = v.id + 10000
    else:
        song_id = v.id
    return PlayedResult(
        song_id=song_id,
        song_name=v.song_name,
        level=v.level,
        level_index=v.level_index,
        type=v.type,
        rating=int(v.dx_rating),
        achievements=v.achievements,
        fc=v.fc,
        fs=v.fs,
        rate=v.rate,
        dx_score=v.dx_score,
        level_value=mai.total_level_value_map[f"{song_id}-{v.level_index}"],
    )


@overload
def lxns_to_playresult(data: list[Score]) -> list[PlayedResult]: ...
@overload
def lxns_to_playresult(
    data: list[Score], *, song: Song | None = None
) -> list[PlayedResult | NotPlayedResult]: ...
def lxns_to_playresult(
    data: list[Score], *, song: Song | None = None
) -> list[PlayedResult | NotPlayedResult]:
    if song:
        r = [
            NotPlayedResult(
                level_value=v.level_value,
                song_id=song.song_id,
                level_index=v.level_index,
            )
            for v in song.difficulties
        ]
    else:
        r = []
    for v in data:
        result = lxns_format_result(v)
        if song:
            r[v.level_index] = result
        else:
            r.append(result)
    return r
