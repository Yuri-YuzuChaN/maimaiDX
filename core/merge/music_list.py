import random
from collections import defaultdict
from copy import deepcopy

from pydantic import RootModel

from .models.song import Difficulties, SimpleSong, Song


class MusicList(RootModel):
    root: list[Song] = []

    def by_id(self, song_id: int) -> Song | None:
        for song in self.root:
            if song.song_id == song_id:
                return song
        return None

    def by_name(self, song_name: str) -> Song | None:
        for song in self.root:
            if song.song_name == song_name:
                return song
        return None

    def by_id_list(self, song_id_list: list[int]) -> list[Song]:
        return [s for s in self.root if s.song_id in set(song_id_list)]

    def by_plan(self, level: str) -> dict[int, list[Difficulties]]:
        result = defaultdict(list)
        for song in self.root:
            for diff in song.difficulties:
                if diff.level == level:
                    result[song.song_id].append(diff)

        return result

    def by_level_list(self) -> dict[str, dict[str, list[SimpleSong]]]:
        temp_result = defaultdict(lambda: defaultdict(list))
        for song in self.root:
            for diff in song.difficulties:
                if "?" in diff.level or diff.level_value < 7:
                    continue

                key = f"{diff.level_value:.1f}"
                temp_result[diff.level][key].append(
                    SimpleSong(
                        song_id=song.song_id,
                        version_str=song.version_str,
                        version_int=song.version_int,
                        type=song.type,
                        difficulties=diff,
                    )
                )
        result = {}

        def lv_sort_func(lv: str):
            v = float(lv.rstrip("+"))
            return (v, 1) if "+" in lv else (v, 0)

        sorted_lvs = sorted(temp_result.keys(), key=lv_sort_func, reverse=True)

        for lv in sorted_lvs:
            sorted_keys = sorted(
                temp_result[lv].keys(), key=lambda x: float(x), reverse=True
            )
            result[lv] = {k: temp_result[lv][k] for k in sorted_keys}

        return result

    def random(self) -> Song:
        return random.choice(self.root)

    def filter(
        self,
        *,
        level: str | list[str] | None = None,
        level_value: float | tuple[float, float] | None = None,
        type: str | list[str] | None = None,
        title: str | None = None,
        artist: str | None = None,
        charter: str | None = None,
        genre: str | list[str] | None = None,
        bpm: float | tuple[float, float] | None = None,
        version_int: int | list[int] | None = None,
        version_str: str | list[str] | None = None,
        all_diff: bool = True,
    ) -> list[Song]:
        def _list(v):
            if v is None:
                return None
            return [v] if not isinstance(v, list) else v

        level = _list(level)
        type = _list(type)
        genre = _list(genre)
        version_int = _list(version_int)
        version_str = _list(version_str)

        new_list = MusicList()

        for song in self.root:
            if title and title.lower() not in song.song_name.lower():
                continue
            if artist and (
                not song.artist or artist.lower() not in song.artist.lower()
            ):
                continue
            if type and song.type not in type:
                continue

            new_song = deepcopy(song)
            new_diffs: list[Difficulties] = []

            for diff in song.difficulties:
                if level and diff.level not in level:
                    continue
                if genre and song.genre not in genre:
                    continue
                if version_int and song.version_int not in version_int:
                    continue
                if version_str and song.version_str not in version_str:
                    continue

                if level_value is not None:
                    if isinstance(level_value, tuple):
                        if not (level_value[0] <= diff.level_value <= level_value[1]):
                            continue
                    else:
                        if diff.level_value != level_value:
                            continue

                if bpm is not None:
                    if isinstance(bpm, tuple):
                        if not (bpm[0] <= song.bpm <= bpm[1]):
                            continue
                    else:
                        if song.bpm != bpm:
                            continue

                if charter and (
                    not diff.note_designer
                    or charter.lower() not in diff.note_designer.lower()
                ):
                    continue

                new_diffs.append(diff)

            if new_diffs:
                if not all_diff:
                    new_song.difficulties = new_diffs
                new_list.root.append(new_song)

        return new_list.root
