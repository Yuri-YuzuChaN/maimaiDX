from ...resources import lxns_alias_file, lxns_music_file
from ..clients.lxns.client import LxnsAPI
from ..clients.lxns.models.music import Aliases, Songs
from ..tool import openfile, writefile


async def get_music_data() -> Songs:
    api = LxnsAPI()
    try:
        data = await api.music_data()
        await writefile(lxns_music_file, data.model_dump())
    except Exception:
        data = Songs.model_validate(await openfile(lxns_music_file))
    return data


async def get_music_aliases() -> Aliases:
    api = LxnsAPI()
    try:
        data = await api.music_alias_data()
        await writefile(lxns_alias_file, data.model_dump())
    except Exception:
        data = Aliases.model_validate(await openfile(lxns_alias_file))
    return data
