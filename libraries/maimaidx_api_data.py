import traceback
from typing import Dict, List, Union

import aiohttp

from .. import log, token

player_error = '''未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。
如未绑定，请前往查分器官网进行绑定
https://www.diving-fish.com/maimaidx/prober/'''
maimaiapi = 'https://www.diving-fish.com/api/maimaidxprober'
ALIAS = {
    'all': 'MaimaiDXAlias',
    'songs': 'GetSongs',
    'alias': 'GetSongsAlias',
    'status': 'GetAliasStatus',
    'apply': 'ApplyAlias',
    'agree': 'AgreeUser',
    'end': 'GetAliasEnd'
}


async def get_player_data(project: str, payload: dict) -> Union[dict, str]:
    """
    获取用户数据，获取失败时返回字符串
    - `project` : 项目
        - `best` : 玩家数据
        - `plate` : 牌子
    - `payload` : 传递给查分器的数据
    """
    if project == 'best':
        p = 'player'
    elif project == 'plate':
        p = 'plate'
    else:
        return '项目错误'
    try:
        async with aiohttp.request('POST', f'{maimaiapi}/query/{p}', json=payload,
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 400:
                data = player_error
            elif resp.status == 403:
                data = '该用户禁止了其他人获取数据。'
            elif resp.status == 200:
                data = await resp.json()
            else:
                data = '未知错误，请联系BOT管理员'
    except Exception as e:
        log.error(f'Error: {traceback.format_exc()}')
        data = f'获取玩家数据时发生错误，请联系BOT管理员: {type(e)}'
    return data


async def get_dev_player_data(payload: dict) -> Union[dict, str]:
    try:
        async with aiohttp.request('GET', f'{maimaiapi}/dev/player/records', headers={'developer-token': token},
                                   params=payload) as resp:
            if resp.status == 400:
                data = player_error
            elif resp.status == 403:
                data = '该用户禁止了其他人获取数据。'
            elif resp.status == 200:
                data = await resp.json()
            else:
                data = '未知错误，请联系BOT管理员'
    except Exception as e:
        log.error(f'Error: {traceback.format_exc()}')
        data = f'获取玩家数据时发生错误，请联系BOT管理员: {type(e)}'
    return data


async def get_rating_ranking_data() -> Union[dict, str]:
    """
    获取排名，获取失败时返回字符串
    """
    try:
        async with aiohttp.request('GET', f'{maimaiapi}/rating_ranking',
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                data = '未知错误，请联系BOT管理员'
            else:
                data = await resp.json()
    except Exception as e:
        log.error(f'Error: {traceback.format_exc()}')
        data = f'获取排名时发生错误，请联系BOT管理员: {type(e)}'
    return data


async def get_music_alias(api: str, params: dict = None) -> Union[
    List[Dict[str, Union[str, int, List[str]]]], Dict[str, Union[str, int, List[str]]]]:
    """
    - `all`: 所有曲目的别名
    - `songs`: 该别名的曲目
    - `alias`: 该曲目的所有别名
    - `status`: 正在进行的别名申请
    - `end`: 已结束的别名申请
    """
    try:
        async with aiohttp.request('GET', f'https://api.yuzuai.xyz/maimaidx/{ALIAS[api]}', params=params,
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 400:
                data = '参数输入错误'
            elif resp.status == 500:
                data = '别名服务器错误，请联系插件开发者'
            else:
                data = await resp.json()
    except Exception as e:
        log.error(f'Error: {traceback.format_exc()}')
        data = f'获取别名时发生错误，请联系BOT管理员: {type(e)}'
    return data


async def get_xray_alias() -> Union[list, str]:
    try:
        async with aiohttp.request('GET', f'https://download.fanyu.site/maimai/alias.json',
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                data = '别名服务器错误，请联系Xray Bot开发者'
            else:
                data = await resp.json()
    except Exception as e:
        log.error(f'Error: {traceback.format_exc()}')
        data = f'获取别名时发生错误，请联系BOT管理员: {type(e)}'
    return data


async def post_music_alias(api: str, params: dict = None) -> Union[
    List[Dict[str, Union[str, int, List[str]]]], Dict[str, Union[str, int, List[str]]]]:
    """
    - `apply`: 申请别名
    - `agree`: 同意别名
    """
    try:
        async with aiohttp.request('POST', f'https://api.yuzuai.xyz/maimaidx/{ALIAS[api]}', params=params,
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 400:
                data = '参数输入错误'
            elif resp.status == 500:
                data = '别名服务器错误，请联系插件开发者'
            else:
                data = await resp.json()
    except Exception as e:
        log.error(f'Error: {traceback.format_exc()}')
        data = f'提交别名时发生错误，请联系BOT管理员: {type(e)}'
    return data
