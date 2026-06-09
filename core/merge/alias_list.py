from pydantic import RootModel

from .models.alias import Alias


class AliasList(RootModel):
    root: list[Alias]

    def by_id(self, music_id: str | int) -> list[Alias]:
        alias_music = []
        for music in self.root:
            if music.song_id == int(music_id):
                alias_music.append(music)
        return alias_music

    def by_alias(self, music_alias: str) -> list[Alias]:
        alias_list = []
        for music in self.root:
            if music_alias in music.alias:
                alias_list.append(music)
        return alias_list
