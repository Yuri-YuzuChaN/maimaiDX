from re import Match

from nonebot import NoneBot, on_startup

from hoshino import Service, priv
from hoshino.typing import CQEvent, MessageSegment

from .libraries.image import image_to_base64, text_to_image
from .libraries.maimaidx_arcade import *

sv_help= """排卡指令如下：
添加机厅 <店名> <地址> <机台数量> 添加机厅信息
删除机厅 <店名> 删除机厅信息
修改机厅 <店名> 数量 <数量> ... 修改机厅信息
添加机厅别名 <店名> <别名>
订阅机厅 <店名> 订阅机厅，简化后续指令
查看订阅 查看群组订阅机厅的信息
取消订阅机厅 <店名> 取消群组机厅订阅
查找机厅,查询机厅,机厅查找,机厅查询 <关键词> 查询对应机厅信息
<店名/别名>人数设置,设定,=,增加,加,+,减少,减,-<人数> 操作排卡人数
<店名/别名>有多少人,有几人,有几卡,几人,几卡 查看排卡人数
机厅几人 查看已订阅机厅排卡人数"""

SV_HELP = '请使用 帮助maimaiDX排卡 查看帮助'
sv_arcade = Service('maimaiDX排卡', manage_priv=priv.ADMIN, enable_on_default=False, help_=SV_HELP)


@on_startup
async def _():
    loga.info('正在获取maimai所有机厅信息')
    await arcade.getArcade()
    loga.info('maimai机厅数据获取完成')


@sv_arcade.on_fullmatch(['帮助maimaiDX排卡', '帮助maimaidx排卡'])
async def dx_arcade_help(bot: NoneBot, ev: CQEvent):
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(sv_help))), at_sender=True)


@sv_arcade.on_prefix(['添加机厅', '新增机厅'])
async def add_arcade(bot: NoneBot, ev: CQEvent):
    args: List[str] = ev.message.extract_plain_text().strip().split()
    if not priv.check_priv(ev, priv.SUPERUSER):
        msg = '仅允许主人添加机厅\n请使用 来杯咖啡+内容 联系主人'
    elif len(args) == 1 and args[0] in ['帮助', 'help', '指令帮助']:
        msg = '添加机厅指令格式：添加机厅 <店名> <位置> <机台数量> <别称1> <别称2> ...'
    elif len(args) >= 3:
        if not args[2].isdigit():
            msg = '格式错误：添加机厅 <店名> <地址> <机台数量> [别称1] [别称2] ...'
        else:
            if not arcade.total.search_fullname(args[0]):
                aid = sorted(arcade.idList, reverse=True)
                if (sid := int(aid[0])) >= 10000:
                    sid += 1
                else:
                    sid = 10000
                arcade_dict = {
                    'name': args[0],
                    'location': args[1],
                    'province': '',
                    'mall': '',
                    'num': int(args[2]) if len(args) > 2 else 1,
                    'id': str(sid),
                    'alias': args[3:] if len(args) > 3 else [],
                    'group': [],
                    'person': 0,
                    'by': '',
                    'time': ''
                }
                arcade.total.add_arcade(arcade_dict)
                await arcade.total.save_arcade()
                msg = f'机厅：{args[0]} 添加成功'
            else:
                msg = f'机厅：{args[0]} 已存在，无法添加机厅'
    else:
        msg = '格式错误：添加机厅 <店名> <地址> <机台数量> [别称1] [别称2] ...'

    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_prefix(['删除机厅', '移除机厅'])
async def delele_arcade(bot: NoneBot, ev: CQEvent):
    name = ev.message.extract_plain_text().strip()
    if not priv.check_priv(ev, priv.SUPERUSER):
        msg = '仅允许主人删除机厅\n请使用 来杯咖啡+内容 联系主人'
    elif not name:
        msg = '格式错误：删除机厅 <店名>，店名需全名'
    else:
        if not arcade.total.search_fullname(name):
            msg = f'未找到机厅：{name}'
        else:
            arcade.total.del_arcade(name)
            await arcade.total.save_arcade()
            msg = f'机厅：{name} 删除成功'
    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_prefix(['添加机厅别名', '删除机厅别名'])
async def _(bot: NoneBot, ev: CQEvent):
    args: List[str] = ev.message.extract_plain_text().strip().split()
    a = True if ev.prefix == '添加机厅别名' else False
    if len(args) != 2:
        msg = '格式错误：添加/删除机厅别名 <店名> <别名>'
    elif not args[0].isdigit() and len(_arc := arcade.total.search_fullname(args[0])) > 1:
        msg = '找到多个相同店名的机厅，请使用店铺ID更改机厅别名\n' + '\n'.join([ f'{_.id}：{_.name}' for _ in _arc ])
    else:
        msg = await update_alias(args[0], args[1], a)
    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_prefix(['修改机厅', '编辑机厅'])
async def modify_arcade(bot: NoneBot, ev: CQEvent):
    args: List[str] = ev.message.extract_plain_text().strip().split()
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员修改机厅信息'
    elif not args[0].isdigit() and len(_arc := arcade.total.search_fullname(args[0])) > 1:
        msg = '找到多个相同店名的机厅，请使用店铺ID修改机厅\n' + '\n'.join([ f'{_.id}：{_.name}' for _ in _arc ])
    elif args[1] == '数量' and len(args) == 3 and args[2].isdigit():
        msg = await updata_arcade(args[0], args[2])
    else:
        msg = '格式错误：修改机厅 <店名> [数量] <数量>'
    
    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_rex(r'^(订阅机厅|取消订阅机厅|取消订阅)\s(.+)', normalize=False)
async def _(bot: NoneBot, ev: CQEvent):
    match: Match[str] = ev['match']
    gid = ev.group_id
    sub = True if match.group(1) == '订阅机厅' else False
    name = match.group(2)
    if not priv.check_priv(ev, priv.ADMIN):
        msg = '仅允许管理员订阅和取消订阅'
    elif not name.isdigit() and len(_arc := arcade.total.search_fullname(name)) > 1:
        msg = f'找到多个相同店名的机厅，请使用店铺ID订阅\n' + '\n'.join([ f'{_.id}：{_.name}' for _ in _arc ])
    else:
        msg = await subscribe(gid, name, sub)
    
    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_fullmatch(['查看订阅', '查看订阅机厅'])
async def check_subscribe(bot: NoneBot, ev: CQEvent):
    gid = int(ev.group_id)
    arcadeList = arcade.total.group_subscribe_arcade(group_id=gid)
    if arcadeList:
        result = [f'群{gid}订阅机厅信息如下：']
        for a in arcadeList:
            alias = "\n  ".join(a.alias)
            result.append(f'''店名：{a.name}
    - 地址：{a.location}
    - 数量：{a.num}
    - 别名：{alias}''')
        msg = '\n'.join(result)
    else:
        msg = '该群未订阅任何机厅'
    await bot.send(ev, msg, at_sender=True)


@sv_arcade.on_prefix(['查找机厅', '查询机厅', '机厅查找', '机厅查询', '搜素机厅', '机厅搜素'])
async def search_arcade(bot: NoneBot, ev: CQEvent):
    name: str = ev.message.extract_plain_text().strip()
    if not name:
        await bot.finish(ev, '格式错误：查找机厅 <关键词>', at_sender=True)
    elif arcade_list := arcade.total.search_name(name):
        result = ['为您找到以下机厅：\n']
        for a in arcade_list:
            result.append(f'''店名：{a.name}
    - 地址：{a.location}
    - ID：{a.id}
    - 数量：{a.num}''')
        if len(arcade_list) < 5:
            await bot.send(ev, '\n==========\n'.join(result), at_sender=True)
        else:
            await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image('\n'.join(result)))), at_sender=True)
    else:
        await bot.send(ev, '没有这样的机厅哦', at_sender=True)


@sv_arcade.on_rex(r'^(.+)?\s?(设置|设定|＝|=|增加|添加|加|＋|\+|减少|降低|减|－|-)\s?([0-9]+|＋|\+|－|-)(人|卡)?$')
async def arcade_person(bot: NoneBot, ev: CQEvent):
    try:
        match: Match[str] = ev['match']
        gid = ev.group_id
        nickname = ev.sender['nickname']
        if not match.group(3).isdigit() and match.group(3) not in ['＋', '+', '－', '-']:
            await bot.finish(ev, '请输入正确的数字', at_sender=True)
        arcade_list = arcade.total.group_subscribe_arcade(group_id=gid)
        if not arcade_list:
            await bot.finish(ev, '该群未订阅机厅，无法更改机厅人数', at_sender=True)
        value = match.group(2)
        person = int(match.group(3))
        if match.group(1):
            if '人数' in match.group(1) or '卡' in match.group(1):
                arcadeName = match.group(1)[:-2] if '人数' in match.group(1) else match.group(1)[:-1]
            else:
                arcadeName = match.group(1)
            _arcade = []
            for _a in arcade_list:
                if arcadeName == _a.name:
                    _arcade.append(_a)
                    break
                if arcadeName in _a.alias:
                    _arcade.append(_a)
                    break
            if not _arcade:
                msg = '已订阅的机厅中未找到该机厅'
            else:
                msg = await update_person(_arcade, nickname, value, person)

            await bot.send(ev, msg, at_sender=True)
    except:
        pass


@sv_arcade.on_fullmatch(['机厅几人', 'jtj'])
async def arcade_query_multiple(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    arcade_list = arcade.total.group_subscribe_arcade(gid)
    if arcade_list:
        result = arcade.total.arcade_to_msg(arcade_list)
        await bot.send(ev, '\n'.join(result))
    else:
        await bot.finish(ev, '该群未订阅任何机厅', at_sender=True)


@sv_arcade.on_suffix(['有多少人', '有几人', '有几卡', '多少人', '多少卡', '几人', 'jr', '几卡'])
async def arcade_query_person(bot: NoneBot, ev: CQEvent):
    gid = ev.group_id
    name = ev.message.extract_plain_text().strip().lower()
    result = None
    if name:
        arcade_list = arcade.total.search_name(name)
        if not arcade_list:
            await bot.finish(ev, '没有这样的机厅哦', at_sender=True)
        result = arcade.total.arcade_to_msg(arcade_list)
        await bot.send(ev, '\n'.join(result))
    else:
        arcade_list = arcade.total.group_subscribe_arcade(gid)
        if arcade_list:
            result = arcade.total.arcade_to_msg(arcade_list)
            await bot.send(ev, '\n'.join(result))
        else:
            await bot.send(ev, '该群未订阅任何机厅，请使用 订阅机厅 <名称> 指令订阅机厅', at_sender=True)


@sv_arcade.scheduled_job('cron', hour='3')
async def _():
    try:
        await download_arcade_info(False)
        for _ in arcade.total:
            _.person = 0
            _.by = '自动清零'
            _.time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        await arcade.total.save_arcade()
    except:
        return
    loga.info('maimaiDX排卡数据更新完毕')