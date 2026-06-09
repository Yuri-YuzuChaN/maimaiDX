import asyncio
from textwrap import dedent

from ...config import log
from ...resources import chart_file, music_file
from ..clients.divingfish.client import DivingFishAPI
from ..clients.divingfish.models import Music, Stats
from ..tool import openfile, writefile

dataerror = dedent("""
    未找到文件，请自行使用浏览器访问 "https://www.diving-fish.com/api/maimaidxprober/music_data" 
    将内容保存为 "music_data.json" 存放在 "static" 目录下并重启bot
""").strip()
charterror = dedent("""
    未找到文件，请自行使用浏览器访问 "https://www.diving-fish.com/api/maimaidxprober/chart_stats"
    将内容保存为 "music_chart.json" 存放在 "static" 目录下并重启bot
""").strip()


async def get_music_list() -> tuple[list[Music], dict[str, list[Stats]]]:
    """获取所有数据"""
    # MusicData
    api = DivingFishAPI()
    try:
        try:
            music_data = await api.music_data()
            await writefile(music_file, music_data)
        except asyncio.exceptions.TimeoutError:
            log.error("maimaiDX曲库数据获取失败，请检查网络环境。已切换至本地暂存文件")
            music_data = await openfile(music_file)
    except FileNotFoundError:
        log.error(dataerror)
        raise FileNotFoundError

    # ChartStats
    try:
        try:
            chart_stats = await api.chart_stats()
            await writefile(chart_file, chart_stats)
        except asyncio.exceptions.TimeoutError:
            log.error("maimaiDX数据获取错误，请检查网络环境，已切换至本地暂存文件")
            chart_stats = await openfile(chart_file)
    except FileNotFoundError:
        log.error(charterror)
        raise FileNotFoundError

    _m = [Music.model_validate(m) for m in music_data]
    _s = {
        n: [Stats.model_validate(_d) for _d in chart_stats["charts"][n]]
        for n in chart_stats["charts"]
    }

    return _m, _s
