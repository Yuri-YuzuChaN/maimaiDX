from nonebot import on_startup

from .command import *
from .libraries.maimai_best_50 import ScoreBaseImage
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
    asyncio.ensure_future(ws_alias_server())
    log.info('正在获取maimai所有曲目信息')
    await mai.get_music()
    log.info('正在获取maimai牌子数据')
    await mai.get_plate_json()
    log.info('正在获取maimai所有曲目别名信息')
    await mai.get_music_alias()
    mai.guess()
    log.info('maimai数据获取完成')
    
    if maiApi.config.saveinmem:
        ScoreBaseImage._load_image()
        log.info('已将图片保存在内存中')
    
    if not list(ratingdir.iterdir()):
        log.warning(
            '<y>注意！注意！</y>检测到定数表文件夹为空！'
            '可能导致「定数表」「完成表」指令无法使用，'
            '请及时私聊BOT使用指令「更新定数表」进行生成。'
        )
    plate_list = [name for name in list(plate_to_dx_version.keys())[1:]]
    platedir_list = [f.name.split('.')[0] for f in platedir.iterdir()]
    cn_list = [name for name in list(platecn.keys())]
    notin = set(plate_list) - set(platedir_list) - set(cn_list)
    if notin:
        anyname = '，'.join(notin)
        log.warning(
            f'<y>注意！注意！</y>未检测到牌子文件夹中的牌子：<y>{anyname}</y>，'
            '可能导致这些牌子的「完成表」指令无法使用，'
            '请及时私聊BOT使用指令「更新完成表」进行生成。'
        )