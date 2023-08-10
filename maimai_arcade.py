from typing import Dict

import aiofiles
from nonebot import NoneBot, on_websocket_connect

from hoshino import Service, priv
from hoshino.typing import CQEvent, MessageSegment

from . import arcades, arcades_json, loga
from .libraries.image import image_to_base64, text_to_image
from .libraries.maimaidx_arcade import *

sv_help= """
排卡指令如下：
添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ... 添加机厅信息
删除机厅 <名称> 删除机厅信息
修改机厅 <名称> [数量/别称] [<数量>/添加/删除] <别称1> <别称2> ... 修改机厅信息
订阅机厅 <名称> 订阅机厅，简化后续指令
查看订阅 查看群组订阅机厅的信息
取消订阅,取消订阅机厅 取消群组机厅订阅
查找机厅,查询机厅,机厅查找,机厅查询 <关键词> 查询对应机厅信息
<名称>人数设置,设定,=,增加,加,+,减少,减,-<人数> 操作排卡人数
<名称>有多少人,有几人,有几卡,几人,几卡 查看排卡人数"""

SV_HELP = '请使用 帮助maimaiDX排卡 查看帮助'
sv_arcade = Service('maimaiDX排卡', manage_priv=priv.ADMIN, enable_on_default=False, help_=SV_HELP)


@on_websocket_connect
async def _(event: CQEvent):
    loga.info('正在获取maimai所有机厅信息')
    await download_arcade_info()
    loga.info('maimai机厅数据获取完成')


@sv_arcade.on_fullmatch(['帮助maimaiDX排卡', '帮助maimaidx排卡'])
async def dx_arcade_help(bot: NoneBot, ev: CQEvent):
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(sv_help))), at_sender=True)


@sv_arcade.on_prefix('添加机厅', '新增机厅')
async def add_arcade(bot: NoneBot, ev: CQEvent):
    args: list[str] = ev.message.extract_plain_text().strip().lower().split()
    if not priv.check_priv(ev, priv.SUPERUSER):
        msg = '仅允许主人添加机厅\n请使用 来杯咖啡+内容 联系主人'
    elif len(args) == 1 and args[0] in ['帮助', 'help', '指令帮助']:
        msg = '添加机厅指令格式：添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ...'
    elif len(args) > 1:
        if len(args) > 3 and not args[2].isdigit():
            msg = '格式错误：添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ...'
        else:
            arcade_dict = {'name': args[0], 'location': args[1],
                           'num': int(args[2]) if len(args) > 2 else 1,
                           'alias': args[3:] if len(args) > 3 else [],
                           'group': [], 'person': 0,
                           'by': '', 'time': ''}
            msg = modify('add', None, arcade_dict)
    else:
        msg = '格式错误：添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ...'

    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_prefix('删除机厅', '移除机厅')
async def delele_arcade(bot: NoneBot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().lower()
    if not priv.check_priv(ev, priv.SUPERUSER):
        msg = '仅允许主人删除机厅\n请使用 来杯咖啡+内容 联系主人'
    elif not args:
        msg = '格式错误：删除机厅 <名称>'
    else:
        msg = modify('delete', None, {'name': args})
    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_prefix('修改机厅', '编辑机厅')
async def modify_arcade(bot: NoneBot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().lower().split()
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员修改机厅信息'
    elif len(args) == 1 and args[0] in ['帮助', 'help', '指令帮助']:
        msg = '修改机厅指令格式：修改机厅 <名称> [数量/别称] [<数量>/添加/删除] <别称1> <别称2> ...'
    elif args[1] == '数量':
        if len(args) == 3 and args[2].isdigit():
            msg = modify('modify', 'num', {'name': args[0], 'num': args[2]})
        else:
            msg = '格式错误：修改机厅 <名称> 数量 <数量>'
    elif args[1] == '别称':
        if args[2] in ['添加', '删除'] and len(args) > 3:
            msg = modify('modify', 'alias_delete' if args[2] == '删除' else 'alias_add',
                    {'name': args[0], 'alias': args[3] if args[2] == '删除' else args[3:]})
        else:
            msg = '格式错误：修改机厅 <名称> 别称 [添加/删除] <别称1> <别称2> ...'
    else:
        msg = '格式错误：修改机厅 <名称> [数量/别称] [<数量>/添加/删除] <别称1> <别称2> ...'
    
    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_prefix('订阅机厅')
async def subscribe_arcade(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    args = ev.message.extract_plain_text().strip().lower()
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '仅允许管理员订阅')
    for a in arcades:
        if gid in a['group']:
            await bot.finish(ev, f'该群已订阅机厅：{a["name"]}', at_sender=True)
    if not args:
        msg = '格式错误：订阅机厅 <名称>'
    else:
        msg = modify('modify', 'subscribe', {'name': args, 'gid': gid})
        
    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_fullmatch('查看订阅', '查看订阅机厅')
async def check_subscribe(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    result = None
    for a in arcades:
        if gid in a['group']:
            result = a
            break
    if result:
        msg = f'''群{gid}订阅机厅信息如下：
{result["name"]} {result["location"]} 机台数量 {result["num"]} {"别称：" if len(result["alias"]) > 0 else ""}{"/".join(result["alias"])}'''.strip()
    else:
        msg = '该群未订阅任何机厅'
    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_fullmatch(['取消订阅', '取消订阅机厅'])
async def unsubscribe_arcade(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '仅允许管理员订阅')
    result = None
    for a in arcades:
        if gid in a['group']:
            result = a
            break
    if result:
        msg = modify('modify', 'unsubscribe', {'name': result['name'], 'gid': gid})
    else:
        msg = '该群未订阅任何机厅，请使用 订阅机厅 <名称> 指令订阅机厅'
    
    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_prefix(['查找机厅', '查询机厅', '机厅查找', '机厅查询', '搜素机厅', '机厅搜素'])
async def search_arcade(bot: NoneBot, ev: CQEvent):
    args: str = ev.message.extract_plain_text().strip().lower()
    if not args:
        await bot.finish(ev, '格式错误：查找机厅 <关键词>', at_sender=True)

    result = []
    for a in arcades:
        match = False
        if args in a['name']:
            match = True
        if args in a['location']:
            match = True
        for alias in a['alias']:
            if args in alias:
                match = True
                break
        if match:
            result.append(a)
    if len(result) == 0:
        await bot.finish(ev, '没有这样的机厅哦', at_sender=True)
    msg = '为您找到以下机厅：\n'
    for r in result:
        msg += f'{r["name"]} {r["location"]} 机台数量 {r["num"]} {"别称：" if len(r["alias"]) > 0 else ""}{"/".join(r["alias"])}'.strip() + '\n'
    if len(result) < 5:
        await bot.send(ev, msg.strip(), at_sender=True)
    else:
        await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg.strip()))), at_sender=True)


@sv_arcade.on_rex(r'^(.+)?\s?(设置|设定|＝|=|增加|添加|加|＋|\+|减少|降低|减|－|-)\s?([0-9]+|＋|\+|－|-)(人|卡)?$')
async def arcade_person(bot: NoneBot, ev: CQEvent):
    try:
        match: Match[str] = ev['match']
        gid = ev.group_id
        nickname = ev.sender['nickname']
        if not match.group(3).isdigit() and match.group(3) not in ['＋', '+', '－', '-']:
            await bot.finish(ev, '请输入正确的数字', at_sender=True)

        msg = arcade_person_data(match, gid, nickname)

        await bot.send(ev, msg, at_sender=True)
    except: pass


@sv_arcade.on_fullmatch(['机厅几人', 'jtj'])
async def arcade_query_multiple(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    group_arcades: Dict[str, list] = {}

    for a in arcades:
        for group_id in a['group']:
            if group_id not in group_arcades:
                group_arcades[group_id] = []
            group_arcades[group_id].append(a)

    if gid in group_arcades:
        arcade = group_arcades[gid]
    else:
        await bot.finish(ev, '该群未配置任何机厅', at_sender=True)

    result = []
    for a in arcade:
        msg = f'{a["name"]}有{a["person"]}人\n'
        if a['num'] > 1:
            msg += f'机均{a["person"] / a["num"]:.2f}人\n'
        if a['by']:
            msg += f'由{a["by"]}更新于{a["time"]}'
        result.append(msg)

    if result:
        await bot.send(ev, '\n'.join(result), at_sender=False)
    else:
        await bot.send(ev, '该群未配置任何机厅', at_sender=True)


@sv_arcade.on_suffix(['有多少人', '有几人', '有几卡', '多少人', '多少卡', '几人', 'jr', '几卡'])
async def arcade_query_person(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    arg = ev.message.extract_plain_text().strip().lower()
    result = None
    if arg:
        for a in arcades:
            if arg == a['name']:
                result = a
                break
            if arg in a['alias']:
                result = a
                break
        if not result:
            await bot.finish(ev, '没有这样的机厅哦', at_sender=True)
    if not result:
        for a in arcades:
            if gid in a['group']:
                result = a
                break
    if result:
        msg = f'{arg}有{result["person"]}人\n'
        if result['num'] > 1:
            msg += f'机均{result["person"] / result["num"]:.2f}人\n'
        if result['by']:
            msg += f'由{result["by"]}更新于{result["time"]}'
        await bot.send(ev, msg.strip(), at_sender=True)
    else:
        await bot.send(ev, '该群未订阅任何机厅，请使用 订阅机厅 <名称> 指令订阅机厅', at_sender=True)


@sv_arcade.scheduled_job('cron', hour='4')
async def Data_Update():
    try:
        await download_arcade_info(False)
        for a in arcades:
            a['person'] = 0
            a['by'] = '自动清零'
            a['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        async with aiofiles.open(arcades_json, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(arcades, ensure_ascii=False, indent=4))
    except:
        return
    loga.info('maimaiDX排卡数据更新完毕')
