from typing import Optional, Dict, List

import aiohttp

plate_to_version = {
        '初': 'maimai',
        '真': 'maimai PLUS',
        '超': 'maimai GreeN',
        '檄': 'maimai GreeN PLUS',
        '橙': 'maimai ORANGE',
        '暁': 'maimai ORANGE PLUS',
        '晓': 'maimai ORANGE PLUS',
        '桃': 'maimai PiNK',
        '櫻': 'maimai PiNK PLUS',
        '樱': 'maimai PiNK PLUS',
        '紫': 'maimai MURASAKi',
        '菫': 'maimai MURASAKi PLUS',
        '堇': 'maimai MURASAKi PLUS',
        '白': 'maimai MiLK',
        '雪': 'MiLK PLUS',
        '輝': 'maimai FiNALE',
        '辉': 'maimai FiNALE',
        '熊': 'maimai でらっくす',
        '華': 'maimai でらっくす PLUS',
        '华': 'maimai でらっくす PLUS',
        '爽': 'maimai でらっくす Splash'
}


async def get_player_plate(payload: Dict):
    async with aiohttp.request("POST", "https://www.diving-fish.com/api/maimaidxprober/query/plate", json=payload) as resp:
        if resp.status == 400:
            return None, 400
        elif resp.status == 403:
            return None, 403
        plate_data = await resp.json()
        return plate_data, 0
