from ...config import log
from ...resources import alias_file, plate_file
from ..clients.yuzuchan.client import YuzuChaNAPI
from ..clients.yuzuchan.models import Alias
from ..tool import openfile, writefile

alias_error = (
    "本地暂存别名文件为空，请自行使用浏览器访问"
    "「https://www.yuzuchan.moe/api/maimaidx/maimaidxalias」"
    "获取别名数据并保存在 'static/music_alias.json' 文件中并重启bot"
)
plate_error = (
    "本地暂存牌子文件为空，请自行使用浏览器访问"
    "「https://www.yuzuchan.moe/api/maimaidx/maimaidxplate」"
    "获取牌子数据并保存在 'static/plate_data.json' 文件中并重启bot"
)


async def get_music_alias_list() -> list[Alias]:
    """获取所有别名"""
    alias_data: list[dict[str, int | str | list[str]]] = []
    try:
        api = YuzuChaNAPI()
        data = await api.get_aliases()
        alias_data = [a.model_dump() for a in data]
        await writefile(alias_file, alias_data)
    except Exception:
        log.error("获取所有曲目别名信息错误，请检查网络环境。已切换至本地暂存文件")
        alias_data = await openfile(alias_file)
        if not alias_data:
            log.error(alias_error)
            raise ValueError

    return [Alias.model_validate(_a) for _a in alias_data]


async def get_plate_data() -> dict[str, list[int]]:
    api = YuzuChaNAPI()
    try:
        plate_data = await api.get_plate_json()
        await writefile(plate_file, plate_data)
    except Exception:
        log.error("获取牌子数据错误，请检查网络环境。已切换至本地暂存文件")
        plate_data = await openfile(plate_file)
        if not plate_data:
            log.error(plate_error)
            raise ValueError
    return plate_data
