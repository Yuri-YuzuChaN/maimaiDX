import json
import time
import traceback
from re import Match
from typing import Union

import aiofiles
import aiohttp

from .. import arcades, arcades_json, loga


async def download_arcade_info(save: bool = True):
    try:
        async with aiohttp.request('GET', 'http://wc.wahlap.net/maidx/rest/location', timeout=aiohttp.ClientTimeout(total=30)) as req:
            if req.status == 200:
                arcades_data = await req.json()
                current_names = [c_a['name'] for c_a in arcades]
                for arcade in arcades_data:
                    if arcade['arcadeName'] not in current_names:
                        arcade_dict = {
                            'name': arcade['arcadeName'],
                            'location': arcade['address'],
                            'province': arcade['province'],
                            'mall': arcade['mall'],
                            'num': arcade['machineCount'],
                            'id': arcade['id'],
                            'alias': [], 'group': [],
                            'person': 0, 'by': '', 'time': ''
                        }
                        arcades.append(arcade_dict)
                    else:
                        arcade_dict = arcades[current_names.index(arcade['arcadeName'])]
                        arcade_dict['location'] = arcade['address']
                        arcade_dict['province'] = arcade['province']
                        arcade_dict['mall'] = arcade['mall']
                        arcade_dict['num'] = arcade['machineCount']
                        arcade_dict['id'] = arcade['id']
                if save:
                    async with aiofiles.open(arcades_json, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(arcades, ensure_ascii=False, indent=4))
            else:
                loga.error('获取机厅信息失败')
    except Exception:
        loga.error(f'Error: {traceback.format_exc()}')
        loga.error('获取机厅信息失败')


def modify(operate: str, arg: str, input_dict: dict) -> str:
    msg = ''
    if operate == 'add':
        if input_dict['name'] in [a['name'] for a in arcades]:
            return '该机厅已存在'
        else:
            arcades.append(input_dict)
            msg = f'添加了机厅：{input_dict["name"]}'
    elif operate == 'delete':
        if input_dict['name'] in [a['name'] for a in arcades]:
            arcades.remove(arcades[[a['name'] for a in arcades].index(input_dict['name'])])
            msg = f'删除了机厅：{input_dict["name"]}'
        else:
            return '无此机厅'
    elif operate == 'modify':
        MAX_CARDS = 30
        if arg == 'num':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcades[[a['name'] for a in arcades].index(input_dict['name'])]['num'] = int(input_dict['num'])
                msg = f'现在的机台数量：{input_dict["num"]}'
            else:
                return '无此机厅'
        elif arg == 'alias_add':
            for i_a in input_dict['alias']:
                for a in arcades:
                    if i_a in a['alias']:
                        return f'已存在别称：{i_a}'
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                arcade['alias'] = list(set(arcade['alias'] + input_dict['alias']))
                msg = f'当前别称：{" ".join(arcade["alias"])}'
            else:
                return '无此机厅'
        elif arg == 'alias_delete':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                if input_dict['alias'] in arcade['alias']:
                    arcade['alias'].remove(input_dict['alias'])
                    if len(arcade['alias']) > 0:
                        msg = f'当前别称：{" ".join(arcade["alias"])}'
                    else:
                        msg = '当前该机厅没有别称'
                else:
                    return f'{arcade["name"]}无此别称'
            else:
                return '无此机厅'
        elif arg == 'subscribe':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                arcade['group'].append(input_dict['gid'])
                msg = f'订阅了机厅：{input_dict["name"]}'
            else:
                return '无此机厅'
        elif arg == 'unsubscribe':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                arcade['group'].remove(input_dict['gid'])
                msg = f'取消订阅了机厅：{input_dict["name"]}'
            else:
                return '无此机厅'
        elif arg == 'person_set':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                if abs(int(input_dict['person']) - arcade['person']) > MAX_CARDS:
                    return f'一次最多改变{MAX_CARDS}卡！'
                if int(input_dict['person']) == arcade["person"]:
                    return f'无变化，现在有{arcade["person"]}卡'
                arcade['person'] = int(input_dict['person'])
                arcade['time'] = input_dict['time']
                arcade['by'] = input_dict['by']
                msg = f'现在有{arcade["person"]}卡'
            else:
                return '无此机厅'
        elif arg == 'person_add':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                if int(input_dict['person']) > MAX_CARDS:
                    return f'一次最多改变{MAX_CARDS}卡！'
                if int(input_dict['person']) == 0:
                    return f'无变化，现在有{arcade["person"]}卡'
                arcade['person'] += int(input_dict['person'])
                arcade['time'] = input_dict['time']
                arcade['by'] = input_dict['by']
                msg = f'现在有{arcade["person"]}卡'
            else:
                return '无此机厅'
        elif arg == 'person_minus':
            if input_dict['name'] in [a['name'] for a in arcades]:
                arcade = arcades[[a['name'] for a in arcades].index(input_dict['name'])]
                if int(input_dict['person']) > MAX_CARDS:
                    return f'一次最多改变{MAX_CARDS}卡！'
                if int(input_dict['person']) == 0:
                    arcade['time'] = input_dict['time']
                    arcade['by'] = input_dict['by']
                    return f'无变化，现在有{arcade["person"]}卡'
                if arcade['person'] < int(input_dict['person']):
                    return f'现在{arcade["person"]}卡，不够减！'
                else:
                    arcade['person'] -= int(input_dict['person'])
                    arcade['time'] = input_dict['time']
                    arcade['by'] = input_dict['by']
                    msg = f'现在有{arcade["person"]}卡'
            else:
                return '无此机厅'
    else:
        return '内部错误，请联系维护组'
    try:
        with open(arcades_json, 'w', encoding='utf-8') as f:
            json.dump(arcades, f, ensure_ascii=False, indent=4)
    except Exception as e:
        traceback.print_exc()
        return f'操作失败，错误代码：{e}'
    return '修改成功！' + msg

def arcade_person_data(match: Match, gid: int, nickname: str) -> Union[str, bool]:
    result = None
    empty_name = False
    if match.group(1):
        if '人数' in match.group(1) or '卡' in match.group(1):
            search_key: str = match.group(1)[:-2] if '人数' in match.group(1) else match.group(1)[:-1]
            if search_key:
                for a in arcades:
                    if search_key.lower() == a['name']:
                        result = a
                        break
                    if search_key.lower() in a['alias']:
                        result = a
                        break
                if not result:
                    return '没有这样的机厅哦'
            else:
                empty_name = True
        else:
            for a in arcades:
                if match.group(1).lower() == a['name']:
                    result = a
                    break
                if match.group(1).lower() in a['alias']:
                    result = a
                    break
            if not result:
                return False
    else:
        return False
    if not result or empty_name:
        for a in arcades:
            if gid in a['group']:
                result = a
                break
    if result:
        msg = ''
        num = match.group(3) if match.group(3).isdigit() else 1
        if match.group(2) in ['设置', '设定', '＝', '=']:
            msg = modify('modify', 'person_set', {'name': result['name'], 'person': num,
                                                  'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                  'by': nickname})
        elif match.group(2) in ['增加', '添加', '加', '＋', '+']:
            msg = modify('modify', 'person_add', {'name': result['name'], 'person': num,
                                                  'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                  'by': nickname})
        elif match.group(2) in ['减少', '降低', '减', '－', '-']:
            msg = modify('modify', 'person_minus', {'name': result['name'], 'person': num,
                                                    'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                    'by': nickname})
        if msg and '一次最多改变' in msg:
            msg = '请勿乱玩bot，恼！'
    else:
        msg = '该群未订阅机厅，请发送 订阅机厅 <名称> 指令订阅机厅'

    return msg