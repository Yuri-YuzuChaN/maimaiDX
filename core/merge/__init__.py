from collections import defaultdict

from ...constants import DX_CN_VERSION
from ...resources import merge_alias_file, merge_music_file
from ..clients.divingfish.models import Music, Notes1, Notes2, Stats
from ..clients.lxns.models import (
    Aliases,
    BuddyNotes,
    Notes,
    SongDifficulty,
    SongDifficultyUtage,
    Songs,
)
from ..clients.lxns.models import Song as LXSong
from ..clients.yuzuchan.models import Alias as YuzuAlias
from ..tool import writefile
from .alias_list import AliasList
from .models import Alias, Difficulties, Song
from .music_list import MusicList


def chart_notes_to_domain(notes: Notes1 | Notes2) -> Notes:
    tap = notes.tap
    hold = notes.hold
    slide = notes.slide
    brk = notes.brk
    touch = getattr(notes, "touch", 0)

    return Notes(
        tap=tap,
        hold=hold,
        slide=slide,
        touch=touch,
        brk=brk,
        total=tap + hold + slide + touch + brk,
    )


def build_difficulty(
    level_index: int,
    level: str,
    level_value: float,
    note_designer: str,
    notes: Notes,
) -> Difficulties:
    return Difficulties(
        level_index=level_index,
        level=level,
        level_value=level_value,
        note_designer=note_designer,
        notes=notes,
        dx_score=notes.total * 3,
        stats=None,
    )


def append_missing_difficulty(song: Song, diffs: list[SongDifficulty]) -> None:
    if len(song.difficulties) == len(diffs):
        return

    diff = diffs[-1]
    song.difficulties.append(
        build_difficulty(
            level_index=diff.difficulty,
            level=diff.level,
            level_value=diff.level_value,
            note_designer=diff.note_designer,
            notes=diff.notes,
        )
    )


async def merge_music_data(
    *,
    diving_fish_list: list[Music],
    lxns_list: Songs | None,
    stats_map: dict[str, list[Stats]],
) -> tuple[MusicList, dict[str, float]]:
    """
    合并 `lxns` 和 `diving-fish` 曲目数据
    """
    song_map: defaultdict[int, Song] = defaultdict(Song)
    level_value_map: defaultdict[str, float] = defaultdict(float)

    if diving_fish_list is None and lxns_list is None:
        raise ValueError

    # diving-fish
    if diving_fish_list is not None:
        for raw in diving_fish_list:
            song_id = int(raw.id)
            song = Song(
                song_id=song_id,
                song_name=raw.title,
                artist=raw.basic_info.artist,
                genre=raw.basic_info.genre,
                bpm=raw.basic_info.bpm,
                version_str=raw.basic_info.version,
                type=raw.type,
                isnew=raw.basic_info.is_new,
            )

            for n, ds in enumerate(raw.ds):
                charts = raw.charts[n]
                notes = chart_notes_to_domain(charts.notes)
                difficulties = Difficulties(
                    level_index=n,
                    level=raw.level[n],
                    level_value=ds,
                    note_designer=charts.charter or "",
                    notes=notes,
                    dx_score=notes.total * 3,
                    stats=None,
                )
                song.difficulties.append(difficulties)
                level_value_map[f"{song_id}-{n}"] = ds

            song_map[song_id] = song

    # lxns
    if lxns_list is not None:
        _version = lxns_list.versions
        ver_map = {v.version: v.title for v in _version}
        new_version = _version[-1].version

        def set_version(
            raw: LXSong,
            ver_type: str,
            sid: int,
            diffs: list[SongDifficulty] | list[SongDifficultyUtage],
        ):
            song = song_map.get(sid)
            base = diffs[0]
            if song is not None:
                song.version_int = base.version
                if isinstance(base, SongDifficultyUtage):
                    song.kanji = base.kanji
                    song.description = base.description
                    song.is_buddy = base.is_buddy
                else:
                    append_missing_difficulty(song, diffs)
                return

            _ver = base.version
            diff_ver = _ver - _ver % 100

            if sid > 100000:
                if isinstance(base.notes, BuddyNotes):
                    _notes = [base.notes.left, base.notes.right]
                else:
                    _notes = [base.notes]
                difficulties = [
                    build_difficulty(
                        level_index=n,
                        level=base.level,
                        level_value=base.level_value,
                        note_designer=base.note_designer,
                        notes=notes,
                    )
                    for n, notes in enumerate(_notes)
                ]
            else:
                difficulties = [
                    build_difficulty(
                        level_index=n,
                        level=d.level,
                        level_value=d.level_value,
                        note_designer=d.note_designer,
                        notes=d.notes,
                    )
                    for n, d in enumerate(diffs)
                ]

            song = Song(
                song_id=sid,
                song_name=raw.title,
                artist=raw.artist,
                genre=raw.genre,
                bpm=raw.bpm,
                version_str=DX_CN_VERSION.get(ver_map[diff_ver])[-1],
                version_int=base.version,
                type=ver_type,
                isnew=new_version == base.version,
                difficulties=difficulties,
            )

            if isinstance(base, SongDifficultyUtage):
                song.kanji = base.kanji
                song.description = base.description
                song.is_buddy = base.is_buddy
            else:
                append_missing_difficulty(song, diffs)

            song_map[sid] = song

        for _raw in lxns_list.songs:
            song_id = _raw.id

            if song_id < 10000:
                if _raw.difficulties.standard:
                    set_version(_raw, "SD", song_id, _raw.difficulties.standard)

                if _raw.difficulties.dx:
                    set_version(_raw, "DX", song_id + 10000, _raw.difficulties.dx)

            elif song_id < 100000:
                if _raw.difficulties.dx:
                    set_version(_raw, "DX", song_id, _raw.difficulties.dx)

                if _raw.difficulties.standard:
                    set_version(_raw, "SD", song_id - 10000, _raw.difficulties.standard)
            else:
                if _raw.difficulties.utage:
                    set_version(_raw, "DX", song_id, _raw.difficulties.utage)

    for sid, stat_list in stats_map.items():
        song = song_map.get(int(sid))
        if song is None:
            continue

        for s in stat_list:
            for diff in song.difficulties:
                if diff.level == s.diff:
                    diff.stats = s
                    break

    result = MusicList(root=song_map.values())
    await writefile(merge_music_file, result.model_dump())

    return result, level_value_map


async def merge_alias_data(
    yuzu_aliases: list[YuzuAlias],
    lxns_aliases: Aliases | None,
    local_alias_data: dict[str, list[str]] | None,
) -> AliasList:
    """
    合并 `lxns` 和 `yuzuchan` 别名数据
    """
    alias_map: dict[int, set[str]] = {}
    song_name_map: dict[int, str] = {}

    for item in yuzu_aliases:
        alias_map.setdefault(item.song_id, set()).update(item.alias)
        if item.name:
            song_name_map.setdefault(item.song_id, item.name)

    if lxns_aliases is not None:
        for item in lxns_aliases.aliases:
            song_id = item.song_id
            if song_id > 1000:
                song_id += 10000
            alias_map.setdefault(song_id, set()).update(item.aliases)

    if local_alias_data is not None:
        for _a, aliases in local_alias_data.items():
            alias_map.setdefault(int(_a), set()).update(aliases)

    result = AliasList(
        root=sorted(
            [
                Alias(
                    song_id=_song_id,
                    song_name=song_name_map.get(_song_id, ""),
                    alias=sorted(aliases),
                )
                for _song_id, aliases in alias_map.items()
                if aliases
            ],
            key=lambda x: x.song_id,
        )
    )
    await writefile(merge_alias_file, result.model_dump())

    return result
