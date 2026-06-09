from ..clients.lxns.models import Aliases
from ..clients.yuzuchan.models import Alias as YuzuAlias
from .models import Alias


def yuzu_alias_to_alias(data: list[YuzuAlias]) -> list[Alias]:
    new_alias_list = []
    for a in data:
        new_alias_list.append(Alias(song_id=a.song_id, song_name=a.name, alias=a.alias))
    return new_alias_list


def lxns_alias_to_alias(data: Aliases) -> list[Alias]:
    new_alias_list = []
    for a in data.aliases:
        new_alias_list.append(Alias(song_id=a.song_id, alias=a.aliases))
    return new_alias_list
