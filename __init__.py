import os, json
from typing import List, Dict
from hoshino.log import new_logger

log = new_logger('maimaiDX')

static = os.path.join(os.path.dirname(__file__), 'static')

config_json = os.path.join(os.path.dirname(__file__), 'config.json')
if not os.path.exists('config.json'):
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump({'enable': [], 'disable': []}, f)
config: Dict[str, List[int]] = json.load(open(config_json, 'r', encoding='utf-8'))

aliases_csv = os.path.join(static, 'aliases.csv')
