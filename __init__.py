import json
import os
from typing import Dict, List

from hoshino.config import NICKNAME
from hoshino.log import new_logger

log = new_logger('maimaiDX')
BOTNAME = NICKNAME if isinstance(NICKNAME, str) else list(NICKNAME)[0]
static = os.path.join(os.path.dirname(__file__), 'static')

arcades_json = os.path.join(static, 'arcades.json')
if not os.path.exists(arcades_json):
    raise FileNotFoundError
arcades: List[Dict] = json.load(open(arcades_json, 'r', encoding='utf-8'))