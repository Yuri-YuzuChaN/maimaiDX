import os
from loguru import logger as log
BOTNAME = 'mokabot'

static = os.path.join(os.path.dirname(__file__), 'static')

__all__ = ['maimai']

from . import *
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='maimaiDX',
    description='移植自 xybot 及 mai-bot 开源项目，基于 HoshinoBotV2 和 nonebot2 的街机音游 舞萌DX 的查询插件',
    usage='',
    extra={'enable_on_default': True}
)
