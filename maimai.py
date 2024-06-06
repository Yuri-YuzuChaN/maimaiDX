from nonebot import on_startup

from .command import *
from .libraries.maimaidx_music import mai

public_addr = 'https://www.yuzuchan.moe/vote'

@on_startup
async def _():
    """bot启动时开始获取所有数据"""
    log.info('正在获取maimai所有曲目信息')
    await mai.get_music()
    log.info('正在获取maimai所有曲目别名信息')
    await mai.get_music_alias()
    log.info('maimai数据获取完成')
    mai.guess()