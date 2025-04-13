from nonebot import on_startup

from .command import *
from .libraries.maimaidx_api_data import maiApi
from .libraries.maimaidx_music import mai


@on_startup
async def _():
    """
    bot启动时开始获取所有数据
    """
    if maiApi.config.maimaidxproberproxy:
        log.info('正在使用代理服务器访问查分器')
    if maiApi.config.maimaidxaliasproxy:
        log.info('正在使用代理服务器访问别名服务器')
    maiApi.load_token_proxy()
    log.info('正在获取maimai所有曲目信息')
    await mai.get_music()
    log.info('正在获取maimai牌子数据')
    await mai.get_plate_json()
    log.info('正在获取maimai所有曲目别名信息')
    await mai.get_music_alias()
    mai.guess()
    log.info('maimai数据获取完成')