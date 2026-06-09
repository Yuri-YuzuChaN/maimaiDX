import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from nonebot import on_startup

from . import commands as commands
from .config import dfconfig, log, lxnsconfig, maiconfig
from .core.alias_ws_push import ws_alias_server
from .core.clients.divingfish.client import DivingFishAPI

from .core.database.qq import create_database
from .core.image.assets import AssetsImage
from .core.service import guess, mai
from .resources import plate_table_dir, rating_table_dir


scheduler = AsyncIOScheduler()
scheduler.add_job(mai.update, "cron", hour=4)


@on_startup
async def _():
    """
    bot启动时开始获取所有数据
    """
    await create_database()
    if dfconfig.divingfish_prober_proxy:
        log.info("使用代理服务器访问「水鱼」查分器")
        DivingFishAPI.set_proxy()
    if maiconfig.maimaidx_alias_proxy:
        log.info("使用代理服务器访问「柚子」别名服务器")

    if maiconfig.maimaidx_alias_push:
        log.opt(colors=True).info("别名推送为「<g>开启</g>」状态")
        asyncio.ensure_future(ws_alias_server())
    else:
        log.opt(colors=True).info("别名推送为「<r>关闭</r>」状态")

    log.info("正在获取maimai曲目数据")
    await mai.get_music()
    log.info("正在获取maimai曲目别名数据")
    await mai.get_music_alias()
    log.info("正在获取maimai牌子数据")
    await mai.get_plate_json()
    guess.guess()
    log.success("猜歌数据初始化完成")
    log.success("maimai数据获取完成")

    if dfconfig.divingfish_token is None:
        log.opt(colors=True).warning(
            "<r>未配置水鱼查分器开发者Token，查分模块只能使用「b50」指令</r>"
        )
    if lxnsconfig.lxns_dev_token is None:
        log.opt(colors=True).warning(
            "<r>未配置落雪查分器开发者Token，无法使用落雪数据源</r>"
        )

    if maiconfig.save_in_memory:
        AssetsImage._load_image()
        log.success("已将图片保存在内存中")

    if not list(rating_table_dir.iterdir()):
        log.opt(colors=True).warning(
            "<y>注意！注意！</y>检测到定数表文件夹为空！"
            "可能导致「定数表」「完成表」指令无法使用，"
            "请及时私聊BOT使用指令「更新定数表」进行生成。"
        )

    if not list(plate_table_dir.iterdir()):
        log.opt(colors=True).warning(
            "<y>注意！注意！</y>检测到牌子文件夹为空！"
            "可能导致「完成表」指令无法使用，"
            "请及时私聊BOT使用指令「更新完成表」进行生成。"
        )
    scheduler.start()