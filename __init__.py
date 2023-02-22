import os

from hoshino.config import NICKNAME
from hoshino.log import new_logger

log = new_logger('maimaiDX')
BOTNAME = {NICKNAME if isinstance(NICKNAME, str) else list(NICKNAME)[0]}
static = os.path.join(os.path.dirname(__file__), 'static')