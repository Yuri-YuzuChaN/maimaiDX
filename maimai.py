import time

from nonebot.typing import State_T

import hoshino.util
from hoshino import Service, priv
from hoshino.typing import CQEvent
from collections import defaultdict
import os, re, asyncio, json, traceback

from .libraries.maimai_best_40 import *
from .libraries.maimai_plate import *
from .libraries.image import *
from .libraries.maimaidx_music import *
from .libraries.tool import hash
from .libraries.maimaidx_guess import *

sv_help = '''
可用命令如下：
帮助maimaiDX 查看指令帮助
项目地址maimaiDX 查看项目地址
今日mai,今日舞萌,今日运势 查看今天的舞萌运势
XXXmaimaiXXX什么 随机一首歌
随个[dx/标准][绿黄红紫白]<难度> 随机一首指定条件的乐曲
查歌<乐曲标题的一部分> 查询符合条件的乐曲
[绿黄红紫白]id <歌曲编号> 查询乐曲信息或谱面信息
<歌曲别名>是什么歌 查询乐曲别名对应的乐曲
<id/歌曲别称>有什么别称 查询乐曲对应的别称 识别id，歌名和别称
定数查歌 <定数>  查询定数对应的乐曲
定数查歌 <定数下限> <定数上限>
分数线 <难度+歌曲id> <分数线> 详情请输入“分数线 帮助”查看
开启/关闭mai猜歌 开关猜歌功能
猜歌 顾名思义，识别id，歌名和别称
b40 <名字> 或 @某人 查B40
b50 <名字> 或 @某人 查B50
我要(在<难度>)上<分数>分 <名字> 或 @某人 查看推荐的上分乐曲
<牌子名称>进度 <名字> 或 @某人 查看牌子完成进度
<等级><评价>进度 <名字> 或 @某人 查看等级评价完成进度
<等级>分数列表<页数> <名字> 或者 @某人 查看等级分数列表（从高至低）
查看排名,查看排行 <页数/名字> 查看某页或某玩家在水鱼网站的用户ra排行
添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ... 添加机厅信息
删除机厅 <名称> 删除机厅信息
修改机厅 <名称> [数量/别称] [<数量>/添加/删除] <别称1> <别称2> ... 修改机厅信息
订阅机厅 <名称> 订阅机厅，简化后续指令
查看订阅 查看群组订阅机厅的信息
取消订阅,取消订阅机厅 取消群组机厅订阅
查找机厅,查询机厅,机厅查找,机厅查询 <关键词> 查询对应机厅信息
<名称>人数设置,设定,=,增加,加,+,减少,减,-<人数> 操作排卡人数
<名称>有多少人,有几人,有几卡,几人,几卡 查看排卡人数
'''.strip()

sv = Service('maimaiDX', manage_priv=priv.ADMIN, enable_on_default=False, help_=sv_help, bundle='maimai')

static = os.path.join(os.path.dirname(__file__), 'static')
player_error = '''未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。
↓ 如未绑定，请前往查分器官网进行绑定 ↓
https://www.diving-fish.com/maimaidx/prober/
'''


def random_music(music: Music) -> str:
    msg = f'''{music.id}. {music.title}
[CQ:image,file=https://www.diving-fish.com/covers/{music.id}.jpg]
{'/'.join(list(map(str, music.ds)))}'''
    return msg


def song_level(ds1: float, ds2: float = None) -> list:
    result = []
    # diff_label = ['Bas', 'Adv', 'Exp', 'Mst', 'ReM']
    if ds2 is not None:
        music_data = total_list.filter(ds=(ds1, ds2))
    else:
        music_data = total_list.filter(ds=ds1)
    for music in sorted(music_data, key = lambda i: int(i['id'])):
        for i in music.diff:
            result.append((music['id'], music['title'], music['ds'][i], diffs[i], music['level'][i], music['stats'][i]['tag']))
    return result


@sv.scheduled_job('cron', hour='5')
async def date_change():
    global total_list, guess_data, arcades
    try:
        for a in arcades:
            a['person'] = 0
            a['by'] = '自动清零'
            a['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        with open(arcades_json, 'w', encoding='utf-8') as f:
            json.dump(arcades, f, ensure_ascii=False, indent=4)
        total_list = get_music_list()
    except:
        return
    guess_data = list(filter(lambda x: x['id'] in hot_music_ids, total_list))


@sv.on_fullmatch(['帮助maimaiDX', '帮助maimaidx'])
async def dx_help(bot, ev: CQEvent):
    await bot.send(ev, f'[CQ:image,file=base64://{image_to_base64(text_to_image(sv_help)).decode()}]', at_sender=True)


@sv.on_fullmatch(['项目地址maimaiDX', '项目地址maimaidx'])
async def dx_help(bot, ev: CQEvent):
    await bot.send(ev, f'项目地址：https://github.com/Yuri-YuzuChaN/maimaiDX\n求star，求宣传~', at_sender=True)


@sv.on_prefix(['定数查歌', 'search base'])
async def search_dx_song_level(bot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().split()
    if len(args) > 2 or len(args) == 0:
        await bot.finish(ev, '命令格式为\n定数查歌 <定数>\n定数查歌 <定数下限> <定数上限>', at_sender=True)
    if len(args) == 1:
        result = song_level(float(args[0]))
    else:
        result = song_level(float(args[0]), float(args[1]))
    if len(result) >= 60:
        await bot.finish(ev, f'结果过多（{len(result)} 条），请缩小搜索范围', at_sender=True)
    msg = ''
    for i in result:
        msg += f'{i[0]}. {i[1]} {i[3]} {i[4]}({i[2]}) {i[5]}\n'
    await bot.finish(ev, f'[CQ:image,file=base64://{image_to_base64(text_to_image(msg.strip())).decode()}]', at_sender=True)


@sv.on_rex(r'^随个((?:dx|sd|标准))?([绿黄红紫白]?)([0-9]+\+?)$')
async def random_song(bot, ev: CQEvent):
    try:
        match = ev['match']
        diff = match.group(1)
        if diff == 'dx':
            tp = ['DX']
        elif diff == 'sd' or diff == '标准':
            tp = ['SD']
        else:
            tp = ['SD', 'DX']
        level = match.group(3)
        if match.group(2) == '':
            music_data = total_list.filter(level=level, type=tp)
        else:
            music_data = total_list.filter(level=level, diff=['绿黄红紫白'.index(match.group(2))], type=tp)
        if len(music_data) == 0:
            msg = '没有这样的乐曲哦。'
        else:
            msg = random_music(music_data.random())
        await bot.send(ev, msg, at_sender=True)
    except:
        await bot.send(ev, '随机命令错误，请检查语法', at_sender=True)


@sv.on_rex(r'.*mai.*什么')
async def random_day_song(bot, ev: CQEvent):
    await bot.send(ev, random_music(total_list.random()))


@sv.on_prefix(['查歌', 'search'])
async def search_song(bot, ev: CQEvent):
    name = ev.message.extract_plain_text().strip()
    if not name:
        return
    result = total_list.filter(title_search=name)
    if len(result) == 0:
        await bot.send(ev, '没有找到这样的乐曲。', at_sender=True)
    elif len(result) < 50:
        search_result = ''
        for music in sorted(result, key=lambda i: int(i['id'])):
            search_result += f'{music["id"]}. {music["title"]}\n'
        await bot.send(ev, search_result.strip(), at_sender=True)
    else:
        await bot.send(ev, f'结果过多（{len(result)} 条），请缩小查询范围。', at_sender=True)


@sv.on_rex(r'^([绿黄红紫白]?)\s?id\s?([0-9]+)$')
async def query_chart(bot, ev: CQEvent):
    match = ev['match']
    level_labels = ['绿', '黄', '红', '紫', '白']
    if match.group(1) != '':
        try:
            level_index = level_labels.index(match.group(1))
            level_name = ['Basic', 'Advanced', 'Expert', 'Master', 'Re: MASTER']
            name = match.group(2)
            music = total_list.by_id(name)
            chart = music['charts'][level_index]
            stats = music['stats'][level_index]
            ds = music['ds'][level_index]
            level = music['level'][level_index]
            if len(chart['notes']) == 4:
                result = f'''{level_name[level_index]} {level}({ds})
TAP: {chart['notes'][0]}
HOLD: {chart['notes'][1]}
SLIDE: {chart['notes'][2]}
BREAK: {chart['notes'][3]}
谱师: {chart['charter']}
难易度参考: {stats['tag']}'''
            else:
                result = f'''{level_name[level_index]} {level}({ds})
TAP: {chart['notes'][0]}
HOLD: {chart['notes'][1]}
SLIDE: {chart['notes'][2]}
TOUCH: {chart['notes'][3]}
BREAK: {chart['notes'][4]}
谱师: {chart['charter']}
难易度参考: {stats['tag']}'''

            msg = f'''
{music["id"]}. {music["title"]}
[CQ:image,file=https://www.diving-fish.com/covers/{music["id"]}.jpg]
{result}'''
            await bot.send(ev, msg, at_sender=True)
        except:
            await bot.send(ev, '未找到该谱面', at_sender=True)
    else:
        try:
            name = match.group(2)
            music = total_list.by_id(name)
            msg = f'''{music["id"]}. {music["title"]}
[CQ:image,file=https://www.diving-fish.com/covers/{music["id"]}.jpg]
艺术家: {music['basic_info']['artist']}
分类: {music['basic_info']['genre']}
BPM: {music['basic_info']['bpm']}
版本: {music['basic_info']['from']}
难度: {'/'.join(list(map(str, music["ds"])))}'''
            await bot.send(ev, msg, at_sender=True)
        except:
            await bot.send(ev, '未找到该乐曲', at_sender=True)


@sv.on_fullmatch(['今日mai', '今日舞萌', '今日运势'])
async def day_mai(bot, ev: CQEvent):
    wm_list = ['拼机', '推分', '越级', '下埋', '夜勤', '练底力', '练手法', '打旧框', '干饭', '抓绝赞', '收歌']
    uid = ev.user_id
    h = hash(uid)
    rp = h % 100
    wm_value = []
    for i in range(11):
        wm_value.append(h & 3)
        h >>= 2
    msg = f'\n今日人品值：{rp}\n'
    for i in range(11):
        if wm_value[i] == 3:
            msg += f'宜 {wm_list[i]}\n'
        elif wm_value[i] == 0:
            msg += f'忌 {wm_list[i]}\n'
    msg += f'{NICKNAME} Bot提醒您：打机时不要大力拍打或滑动哦\n今日推荐歌曲：'
    music = total_list[h % len(total_list)]
    msg += random_music(music)
    await bot.send(ev, msg, at_sender=True)

music_aliases = defaultdict(list)
f = open(os.path.join(static, 'aliases.csv'), 'r', encoding='utf-8')
tmp = f.readlines()
f.close()
for t in tmp:
    arr = t.strip().split('\t')
    for i in range(len(arr)):
        if arr[i] != '':
            music_aliases[arr[i].lower()].append(arr[0])


@sv.on_suffix(['是什么歌', '是啥歌'])
async def what_song(bot, ev: CQEvent):
    name = ev.message.extract_plain_text().strip().lower()
    if name not in music_aliases:
        await bot.finish(ev, '未找到此歌曲\n舞萌 DX 歌曲别名收集计划：https://docs.qq.com/sheet/DQ0pvUHh6b1hjcGpl', at_sender=True)
    result = music_aliases[name]
    if len(result) == 1:
        music = total_list.by_title(result[0])
        await bot.send(ev, '您要找的是不是：' + random_music(music), at_sender=True)
    else:
        msg = '\n'.join(result)
        await bot.send(ev, f'您要找的可能是以下歌曲中的其中一首：\n{msg}', at_sender=True)


@sv.on_suffix('有什么别称')
async def how_song(bot, ev: CQEvent):
    name = ev.message.extract_plain_text().strip().lower()
    if name.isdigit():
        music = total_list.by_id(name)
        if music:
            title = music_aliases[music.title.lower()]
        else:
            await bot.finish(ev, '未找到此歌曲', at_sender=True)
    else:
        if name not in music_aliases:
            await bot.finish(ev, '未找到此歌曲', at_sender=True)
        title = music_aliases[name]
    result = []
    for key, value in music_aliases.items():
        for t in title:
            if t in value and key not in result:
                result.append(key)
    if len(result) == 0 or len(result) == 1:
        await bot.finish(ev, '该曲目没有别称', at_sender=True)
    else:
        msg = f'该曲目有以下别称：\n'
        for r in result:
            msg += f'{r}\n'
        await bot.send(ev, msg, at_sender=True)


@sv.on_prefix('分数线')
async def quert_score(bot, ev: CQEvent):
    text = ev.message.extract_plain_text().strip()
    args = ev.message.extract_plain_text().strip().split()
    if len(args) == 1 and args[0] == '帮助':
        msg = '''此功能为查找某首歌分数线设计。
命令格式：分数线 <难度+歌曲id> <分数线>
例如：分数线 紫799 100
命令将返回分数线允许的 TAP GREAT 容错以及 BREAK 50落等价的 TAP GREAT 数。
以下为 TAP GREAT 的对应表：
GREAT/GOOD/MISS
TAP\t1/2.5/5
HOLD\t2/5/10
SLIDE\t3/7.5/15
TOUCH\t1/2.5/5
BREAK\t5/12.5/25(外加200落)'''
        await bot.send(ev, f'[CQ:image,file=base64://{image_to_base64(text_to_image(msg)).decode()}]', at_sender=True)
    else:
        try:
            result = re.search(r'([绿黄红紫白])\s?([0-9]+)', text)
            level_labels = ['绿', '黄', '红', '紫', '白']
            level_labels2 = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:MASTER']
            level_index = level_labels.index(result.group(1))
            chart_id = result.group(2)
            line = float(args[-1])
            music = total_list.by_id(chart_id)
            chart: Dict[Any] = music['charts'][level_index]
            tap = int(chart['notes'][0])
            slide = int(chart['notes'][2])
            hold = int(chart['notes'][1])
            touch = int(chart['notes'][3]) if len(chart['notes']) == 5 else 0
            brk = int(chart['notes'][-1])
            total_score = 500 * tap + slide * 1500 + hold * 1000 + touch * 500 + brk * 2500
            break_bonus = 0.01 / brk
            break_50_reduce = total_score * break_bonus / 4
            reduce = 101 - line
            if reduce <= 0 or reduce >= 101:
                raise ValueError
            msg = f'''{music['title']} {level_labels2[level_index]}
分数线 {line}% 允许的最多 TAP GREAT 数量为 {(total_score * reduce / 10000):.2f}(每个-{10000 / total_score:.4f}%),
BREAK 50落(一共{brk}个)等价于 {(break_50_reduce / 100):.3f} 个 TAP GREAT(-{break_50_reduce / total_score * 100:.4f}%)'''
            await bot.send(ev, msg, at_sender=True)
        except:
            await bot.send(ev, '格式错误，输入“分数线 帮助”以查看帮助信息', at_sender=True)


@sv.on_rex(r'^[Bb]([45])0\s?(.+)?$')
async def best_40(bot, ev: CQEvent):
    ret = re.search(r"\[CQ:at,qq=(.*)\]", str(ev.raw_message))
    match = ev['match']
    if match.group(2) and ret:
        await bot.finish(ev, '搁着卡bug呢？', at_sender=True)
    elif not match.group(2) or ret:
        if ret:
            payload = {'qq': ret.group(1)}
        else:
            payload = {'qq': str(ev.user_id)}
    else:
        payload = {'username': match.group(2).strip()}
    if match.group(1) == '5': payload['b50'] = True
    img, success = await generate(payload)
    if success == 400:
        await bot.send(ev, player_error, at_sender=True)
    elif success == 403:
        await bot.send(ev, '该用户禁止了其他人获取数据。', at_sender=True)
    else:
        await bot.send(ev, f'[CQ:image,file=base64://{image_to_base64(img).decode()}]', at_sender=True)


@sv.on_rex(r'^我要在?([0-9]+\+?)?上([0-9]+)分\s?(.+)?')  # 慎用，垃圾代码非常吃机器性能
async def rise_score(bot, ev: CQEvent):
    ret = re.search(r"\[CQ:at,qq=(.*)\]", str(ev.raw_message))
    match = ev['match']
    if match.group(1) and match.group(1) not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    if match.group(2) and ret:
        await bot.finish(ev, '搁着卡bug呢？', at_sender=True)
    elif not match.group(3) or ret:
        if ret:
            payload = {'qq': ret.group(1)}
        else:
            payload = {'qq': str(ev.user_id)}
    else:
        payload = {'username': match.group(3).strip()}
    player_data, success = await get_player_data(payload)
    if success == 400:
        await bot.send(ev, player_error, at_sender=True)
    elif success == 403:
        await bot.send(ev, '该用户禁止了其他人获取数据。', at_sender=True)
    else:
        dx_ra_lowest = 999
        sd_ra_lowest = 999
        player_dx_list = []
        player_sd_list = []
        music_dx_list = []
        music_sd_list = []
        for dx in player_data['charts']['dx']:
            dx_ra_lowest = min(dx_ra_lowest, dx['ra'])
            player_dx_list.append([int(dx['song_id']), int(dx["level_index"]), int(dx['ra'])])
        for sd in player_data['charts']['sd']:
            sd_ra_lowest = min(sd_ra_lowest, sd['ra'])
            player_sd_list.append([int(sd['song_id']), int(sd["level_index"]), int(sd['ra'])])
        player_dx_id_list = [[d[0], d[1]] for d in player_dx_list]
        player_sd_id_list = [[s[0], s[1]] for s in player_sd_list]
        for music in total_list:
            for i, achievement in enumerate(achievementList):
                for j, ds in enumerate(music.ds):
                    if match.group(1) and music['level'][j] != match.group(1): continue
                    if music.is_new:
                        music_ra = computeRa(ds, achievement)
                        if music_ra < dx_ra_lowest: continue
                        if [int(music.id), j] in player_dx_id_list:
                            player_ra = player_dx_list[player_dx_id_list.index([int(music.id), j])][2]
                            if music_ra - player_ra == int(match.group(2)) and [int(music.id), j, music_ra] not in player_dx_list:
                                music_dx_list.append([music, diffs[j], ds, achievement, scoreRank[i + 1].upper(), music_ra, music.stats[j].difficulty])
                        else:
                            if music_ra - dx_ra_lowest == int(match.group(2)) and [int(music.id), j, music_ra] not in player_dx_list:
                                music_dx_list.append([music, diffs[j], ds, achievement, scoreRank[i + 1].upper(), music_ra, music.stats[j].difficulty])
                    else:
                        music_ra = computeRa(ds, achievement)
                        if music_ra < sd_ra_lowest: continue
                        if [int(music.id), j] in player_sd_id_list:
                            player_ra = player_sd_list[player_sd_id_list.index([int(music.id), j])][2]
                            if music_ra - player_ra == int(match.group(2)) and [int(music.id), j, music_ra] not in player_sd_list:
                                music_sd_list.append([music, diffs[j], ds, achievement, scoreRank[i + 1].upper(), music_ra, music.stats[j].difficulty])
                        else:
                            if music_ra - sd_ra_lowest == int(match.group(2)) and [int(music.id), j, music_ra] not in player_sd_list:
                                music_sd_list.append([music, diffs[j], ds, achievement, scoreRank[i + 1].upper(), music_ra, music.stats[j].difficulty])
        if len(music_dx_list) == 0 and len(music_sd_list) == 0:
            await bot.finish(ev, '没有找到这样的乐曲', at_sender=True)
        elif len(music_dx_list) + len(music_sd_list) > 60:
            await bot.finish(ev, f'结果过多（{len(music_dx_list) + len(music_sd_list)} 条），请缩小查询范围。', at_sender=True)
        appellation = ("您" if not match.group(3) else match.group(3)) if not ret else ret.group(1)
        msg = ''
        if len(music_sd_list) != 0:
            msg += f'为{appellation}推荐以下标准乐曲：\n'
            for music, diff, ds, achievement, rank, ra, difficulty in sorted(music_sd_list, key=lambda i: int(i[0]['id'])):
                msg += f'{music["id"]}. {music["title"]} {diff} {ds} {achievement} {rank} {ra} {difficulty}\n'
        if len(music_dx_list) != 0:
            msg += f'\n为{appellation}推荐以下2021乐曲：\n'
            for music, diff, ds, achievement, rank, ra, difficulty in sorted(music_dx_list, key=lambda i: int(i[0]['id'])):
                msg += f'{music["id"]}. {music["title"]} {diff} {ds} {achievement} {rank} {ra} {difficulty}\n'
        await bot.send(ev, f'[CQ:image,file=base64://{image_to_base64(text_to_image(msg.strip())).decode()}]', at_sender=True)


@sv.on_rex(r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽舞霸])([極极将舞神者]舞?)进度\s?(.+)?')
async def plate_process(bot, ev: CQEvent):
    ret = re.search(r"\[CQ:at,qq=(.*)\]", str(ev.raw_message))
    match = ev['match']
    if f'{match.group(1)}{match.group(2)}' == '真将':
        await bot.finish(ev, '真系没有真将哦', at_sender=True)
    if match.group(2) and ret:
        await bot.finish(ev, '搁着卡bug呢？', at_sender=True)
    elif not match.group(3) or ret:
        if ret:
            payload = {'qq': ret.group(1)}
        else:
            payload = {'qq': str(ev.user_id)}
    else:
        payload = {'username': match.group(3).strip()}
    if match.group(1) in ['舞', '霸']:
        payload['version'] = list(set(version for version in plate_to_version.values()))
    else:
        payload['version'] = [plate_to_version[match.group(1)]]
    player_data, success = await get_player_plate(payload)
    if success == 400:
        await bot.send(ev, player_error, at_sender=True)
    elif success == 403:
        await bot.send(ev, '该用户禁止了其他人获取数据。', at_sender=True)
    else:
        song_played = []
        song_remain_expert = []
        song_remain_master = []
        song_remain_re_master = []
        song_remain_difficult = []
        if match.group(2) in ['将', '者']:
            for song in player_data['verlist']:
                if song['level_index'] == 2 and song['achievements'] < (100.0 if match.group(2) == '将' else 80.0):
                    song_remain_expert.append([song['id'], song['level_index']])
                if song['level_index'] == 3 and song['achievements'] < (100.0 if match.group(2) == '将' else 80.0):
                    song_remain_master.append([song['id'], song['level_index']])
                if match.group(1) in ['舞', '霸'] and song['level_index'] == 4 and song['achievements'] < (100.0 if match.group(2) == '将' else 80.0):
                    song_remain_re_master.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        elif match.group(2) in ['極', '极']:
            for song in player_data['verlist']:
                if song['level_index'] == 2 and not song['fc']:
                    song_remain_expert.append([song['id'], song['level_index']])
                if song['level_index'] == 3 and not song['fc']:
                    song_remain_master.append([song['id'], song['level_index']])
                if match.group(1) == '舞' and song['level_index'] == 4 and not song['fc']:
                    song_remain_re_master.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        elif match.group(2) == '舞舞':
            for song in player_data['verlist']:
                if song['level_index'] == 2 and song['fs'] not in ['fsd', 'fsdp']:
                    song_remain_expert.append([song['id'], song['level_index']])
                if song['level_index'] == 3 and song['fs'] not in ['fsd', 'fsdp']:
                    song_remain_master.append([song['id'], song['level_index']])
                if match.group(1) == '舞' and song['level_index'] == 4 and song['fs'] not in ['fsd', 'fsdp']:
                    song_remain_re_master.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        elif match.group(2) == '神':
            for song in player_data['verlist']:
                if song['level_index'] == 2 and song['fc'] not in ['ap', 'app']:
                    song_remain_expert.append([song['id'], song['level_index']])
                if song['level_index'] == 3 and song['fc'] not in ['ap', 'app']:
                    song_remain_master.append([song['id'], song['level_index']])
                if match.group(1) == '舞' and song['level_index'] == 4 and song['fc'] not in ['ap', 'app']:
                    song_remain_re_master.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        for music in total_list:
            if music.version in payload['version']:
                if [int(music.id), 2] not in song_played:
                    song_remain_expert.append([int(music.id), 2])
                if [int(music.id), 3] not in song_played:
                    song_remain_master.append([int(music.id), 3])
                if match.group(1) in ['舞', '霸'] and len(music.level) == 5 and [int(music.id), 4] not in song_played:
                    song_remain_re_master.append([int(music.id), 4])
        song_remain_expert = sorted(song_remain_expert, key=lambda i: int(i[0]))
        song_remain_master = sorted(song_remain_master, key=lambda i: int(i[0]))
        song_remain_re_master = sorted(song_remain_re_master, key=lambda i: int(i[0]))
        for song in song_remain_expert + song_remain_master + song_remain_re_master:
            music = total_list.by_id(str(song[0]))
            if music.ds[song[1]] > 13.6:
                song_remain_difficult.append([music.id, music.title, diffs[song[1]], music.ds[song[1]], music.stats[song[1]].difficulty, song[1]])
        appellation = ("您" if not match.group(3) else match.group(3)) if not ret else ret.group(1)
        msg = f'''{appellation}的{match.group(1)}{match.group(2)}剩余进度如下：
Expert剩余{len(song_remain_expert)}首
Master剩余{len(song_remain_master)}首
'''
        song_remain = song_remain_expert + song_remain_master + song_remain_re_master
        song_record = [[s['id'], s['level_index']] for s in player_data['verlist']]
        if match.group(1) in ['舞', '霸']:
            msg += f'Re:Master剩余{len(song_remain_re_master)}首\n'
        if len(song_remain_difficult) > 0:
            if len(song_remain_difficult) < 11:
                msg += '剩余定数大于13.6的曲目：\n'
                for i, s in enumerate(sorted(song_remain_difficult, key=lambda i: i[3])):
                    self_record = ''
                    if [int(s[0]), s[-1]] in song_record:
                        record_index = song_record.index([int(s[0]), s[-1]])
                        if match.group(2) in ['将', '者']:
                            self_record = str(player_data['verlist'][record_index]['achievements']) + '%'
                        elif match.group(2) in ['極', '极', '神']:
                            if player_data['verlist'][record_index]['fc']:
                                self_record = comboRank[combo_rank.index(player_data['verlist'][record_index]['fc'])].upper()
                        elif match.group(2) == '舞舞':
                            if player_data['verlist'][record_index]['fs']:
                                self_record = syncRank[sync_rank.index(player_data['verlist'][record_index]['fs'])].upper()
                    msg += f'No.{i + 1} {s[0]}. {s[1]} {s[2]} {s[3]} {s[4]} {self_record}'.strip() + '\n'
            else: msg += f'还有{len(song_remain_difficult)}首大于13.6定数的曲目，加油推分捏！\n'
        elif len(song_remain) > 0:
            if len(song_remain) < 11:
                msg += '剩余曲目：\n'
                for i, s in enumerate(sorted(song_remain, key=lambda i: i[3])):
                    m = total_list.by_id(str(s[0]))
                    self_record = ''
                    if [int(s[0]), s[-1]] in song_record:
                        record_index = song_record.index([int(s[0]), s[-1]])
                        if match.group(2) in ['将', '者']:
                            self_record = str(player_data['verlist'][record_index]['achievements']) + '%'
                        elif match.group(2) in ['極', '极', '神']:
                            if player_data['verlist'][record_index]['fc']:
                                self_record = comboRank[combo_rank.index(player_data['verlist'][record_index]['fc'])].upper()
                        elif match.group(2) == '舞舞':
                            if player_data['verlist'][record_index]['fs']:
                                self_record = syncRank[sync_rank.index(player_data['verlist'][record_index]['fs'])].upper()
                    msg += f'No.{i + 1} {m.id}. {m.title} {diffs[s[1]]} {m.ds[s[1]]} {m.stats[s[1]].difficulty} {self_record}'.strip() + '\n'
            else:
                msg += '已经没有定数大于13.6的曲目了,加油清谱捏！\n'
        else: msg += f'恭喜{appellation}完成{match.group(1)}{match.group(2)}！'
        await bot.send(ev, msg.strip(), at_sender=True)


@sv.on_rex(r'^([0-9]+\+?)\s?(.+)进度\s?(.+)?')
async def level_process(bot, ev: CQEvent):
    ret = re.search(r"\[CQ:at,qq=(.*)\]", str(ev.raw_message))
    match = ev['match']
    if match.group(1) not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    if match.group(2).lower() not in scoreRank + comboRank + syncRank:
        await bot.finish(ev, '无此评价等级', at_sender=True)
    if levelList.index(match.group(1)) < 11 or (match.group(2).lower() in scoreRank and scoreRank.index(match.group(2).lower()) < 8):
        await bot.finish(ev, '兄啊，有点志向好不好', at_sender=True)
    if match.group(2) and ret:
        await bot.finish(ev, '搁着卡bug呢？', at_sender=True)
    elif not match.group(3) or ret:
        if ret:
            payload = {'qq': ret.group(1)}
        else:
            payload = {'qq': str(ev.user_id)}
    else:
        payload = {'username': match.group(3).strip()}
    payload['version'] = list(set(version for version in plate_to_version.values()))
    player_data, success = await get_player_plate(payload)
    if success == 400:
        await bot.send(ev, player_error, at_sender=True)
    elif success == 403:
        await bot.send(ev, '该用户禁止了其他人获取数据。', at_sender=True)
    else:
        song_played = []
        song_remain = []
        if match.group(2).lower() in scoreRank:
            achievement = achievementList[scoreRank.index(match.group(2).lower()) - 1]
            for song in player_data['verlist']:
                if song['level'] == match.group(1) and song['achievements'] < achievement:
                    song_remain.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        elif match.group(2).lower() in comboRank:
            combo_index = comboRank.index(match.group(2).lower())
            for song in player_data['verlist']:
                if song['level'] == match.group(1) and ((song['fc'] and combo_rank.index(song['fc']) < combo_index) or not song['fc']):
                    song_remain.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        elif match.group(2).lower() in syncRank:
            sync_index = syncRank.index(match.group(2).lower())
            for song in player_data['verlist']:
                if song['level'] == match.group(1) and ((song['fs'] and sync_rank.index(song['fs']) < sync_index) or not song['fs']):
                    song_remain.append([song['id'], song['level_index']])
                song_played.append([song['id'], song['level_index']])
        for music in total_list:
            for i, lv in enumerate(music.level[2:]):
                if lv == match.group(1) and [int(music.id), i + 2] not in song_played:
                    song_remain.append([int(music.id), i + 2])
        song_remain = sorted(song_remain, key=lambda i: int(i[1]))
        song_remain = sorted(song_remain, key=lambda i: int(i[0]))
        songs = []
        for song in song_remain:
            music = total_list.by_id(str(song[0]))
            songs.append([music.id, music.title, diffs[song[1]], music.ds[song[1]], music.stats[song[1]].difficulty, song[1]])
        appellation = ("您" if not match.group(3) else match.group(3)) if not ret else ret.group(1)
        msg = ''
        if len(song_remain) > 0:
            if len(song_remain) < 50:
                song_record = [[s['id'], s['level_index']] for s in player_data['verlist']]
                msg += f'{appellation}的{match.group(1)}全谱面{match.group(2).upper()}剩余曲目如下：\n'
                for i, s in enumerate(sorted(songs, key=lambda i: i[3])):
                    self_record = ''
                    if [int(s[0]), s[-1]] in song_record:
                        record_index = song_record.index([int(s[0]), s[-1]])
                        if match.group(2).lower() in scoreRank:
                            self_record = str(player_data['verlist'][record_index]['achievements']) + '%'
                        elif match.group(2).lower() in comboRank:
                            if player_data['verlist'][record_index]['fc']:
                                self_record = comboRank[combo_rank.index(player_data['verlist'][record_index]['fc'])].upper()
                        elif match.group(2).lower() in syncRank:
                            if player_data['verlist'][record_index]['fs']:
                                self_record = syncRank[sync_rank.index(player_data['verlist'][record_index]['fs'])].upper()
                    msg += f'No.{i + 1} {s[0]}. {s[1]} {s[2]} {s[3]} {s[4]} {self_record}'.strip() + '\n'
            else:
                await bot.finish(ev, f'{appellation}还有{len(song_remain)}首{match.group(1)}曲目没有达成{match.group(2).upper()},加油推分捏！', at_sender=True)
        else:
            await bot.finish(ev, f'恭喜{appellation}达成{match.group(1)}全谱面{match.group(2).upper()}！', at_sender=True)
        await bot.send(ev, f'[CQ:image,file=base64://{image_to_base64(text_to_image(msg.strip())).decode()}]', at_sender=True)


@sv.on_rex(r'^([0-9]+\+?)分数列表\s?([0-9]+)?\s?(.+)?')
async def level_achievement_list(bot, ev: CQEvent):
    ret = re.search(r"\[CQ:at,qq=(.*)\]", str(ev.raw_message))
    match = ev['match']
    if match.group(1) not in levelList:
        await bot.finish(ev, '无此等级', at_sender=True)
    if match.group(2) and ret:
        await bot.finish(ev, '搁着卡bug呢？', at_sender=True)
    elif not match.group(3) or ret:
        if ret:
            payload = {'qq': ret.group(1)}
        else:
            payload = {'qq': str(ev.user_id)}
    else:
        payload = {'username': match.group(3).strip()}
    payload['version'] = list(set(version for version in plate_to_version.values()))
    player_data, success = await get_player_plate(payload)
    if success == 400:
        await bot.send(ev, player_error, at_sender=True)
    elif success == 403:
        await bot.send(ev, '该用户禁止了其他人获取数据。', at_sender=True)
    else:
        song_list = []
        for song in player_data['verlist']:
            if song['level'] == match.group(1):
                song_list.append(song)
        SONGS_PER_PAGE = 25
        if match.group(2): page = max(min(int(match.group(2)), len(song_list) // SONGS_PER_PAGE + 1), 1)
        else: page = 1
        appellation = ("您" if not match.group(3) else match.group(3)) if not ret else ret.group(1)
        msg = f'{appellation}的{match.group(1)}分数列表（从高至低）：\n'
        for i, s in enumerate(sorted(song_list, key=lambda i: i['achievements'], reverse=True)):
            if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
                m = total_list.by_id(str(s['id']))
                msg += f'No.{(page - 1) * SONGS_PER_PAGE + i + 1} {s["achievements"]:.4f} {m.id}. {m.title} {diffs[s["level_index"]]} {m.ds[s["level_index"]]} {m.stats[s["level_index"]].difficulty}'
                if s["fc"]: msg += f' {comboRank[combo_rank.index(s["fc"])].upper()}'
                if s["fs"]: msg += f' {syncRank[sync_rank.index(s["fs"])].upper()}'
                msg += '\n'
        msg += f'第{page}页，共{len(song_list) // SONGS_PER_PAGE + 1}页'
        await bot.send(ev, f'[CQ:image,file=base64://{image_to_base64(text_to_image(msg.strip())).decode()}]', at_sender=True)


@sv.on_prefix(['查看排名', '查看排行'])
async def level_process(bot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().split()
    page = 1
    name = ''
    if len(args) == 1:
        if args[0].isdigit():
            page = int(args[0])
        else:
            name = args[0].lower()
    async with aiohttp.request("GET", "https://www.diving-fish.com/api/maimaidxprober/rating_ranking") as resp:
        rank_data = await resp.json()
        sorted_rank_data = sorted(rank_data, key=lambda r: r['ra'], reverse=True)
        if name:
            if name in [r['username'].lower() for r in sorted_rank_data]:
                rank_index = [r['username'].lower() for r in sorted_rank_data].index(name) + 1
                nickname = sorted_rank_data[rank_index - 1]['username']
                await bot.send(ev, f'截止至 {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}\n玩家 {nickname} 在Diving Fish网站已注册用户ra排行第{rank_index}', at_sender=True)
            else:
                await bot.send(ev, '未找到该玩家', at_sender=True)
        else:
            user_num = len(sorted_rank_data)
            msg = f'截止至 {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}，Diving Fish网站已注册用户ra排行：\n'
            if page * 50 > user_num:
                page = user_num // 50 + 1
            end = page * 50 if page * 50 < user_num else user_num
            for i, ranker in enumerate(sorted_rank_data[(page - 1) * 50:end]):
                msg += f'{i + 1 + (page - 1) * 50}. {ranker["username"]} {ranker["ra"]}\n'
            msg += f'第{page}页，共{user_num // 50 + 1}页'
            await bot.send(ev, f'[CQ:image,file=base64://{image_to_base64(text_to_image(msg.strip())).decode()}]', at_sender=True)


guess_dict: Dict[Tuple[str], GuessObject] = {}
guess_time_dict: Dict[Tuple[str], float] = {}


async def guess_music_loop(bot, ev: CQEvent, state: State_T):
    cycle = state['cycle']
    if cycle != 0:
        await asyncio.sleep(8)
    else:
        await asyncio.sleep(4)
    guess: GuessObject = state['guess_object']
    if ev.group_id not in config['enable'] or guess.is_end:
        return
    if cycle < 6:
        await bot.send(ev, f'{cycle + 1}/7 这首歌{guess.guess_options[cycle]}')
    else:
        msg = f'''7/7 这首歌封面的一部分是：
[CQ:image,file=base64://{guess.b64image.decode()}]
答案将在30秒后揭晓'''
        await bot.send(ev, msg)
        await give_answer(bot, ev, state)
    state['cycle'] += 1
    await guess_music_loop(bot, ev, state)


async def give_answer(bot, ev: CQEvent, state: State_T):
    await asyncio.sleep(30)
    guess: GuessObject = state['guess_object']
    if ev.group_id not in config['enable'] or guess.is_end:
        return
    guess.is_end = True
    del guess_dict[state['gid']]
    msg = f'''答案是：
{random_music(guess.music)}'''
    await bot.finish(ev, msg)


@sv.on_fullmatch('猜歌')
async def guess_music(bot, ev: CQEvent):
    gid = ev.group_id
    if gid not in config['enable']:
        await bot.finish(ev, '该群已关闭猜歌功能，开启请输入 开启mai猜歌')
    if gid in guess_dict:
        if gid in guess_time_dict and time.time() > guess_time_dict[gid] + 120:  # 如果已经过了 120 秒则自动结束上一次
            await bot.send(ev, '检测到卡死的猜歌进程，已清除')
            del guess_dict[gid]
        else: await bot.finish(ev, '当前已有正在进行的猜歌')

    guess = GuessObject()
    guess_dict[gid] = guess
    guess_time_dict[gid] = time.time()
    state: State_T = {'gid': gid, 'guess_object': guess, 'cycle': 0}
    await bot.send(ev, '我将从热门乐曲中选择一首歌，每隔8秒描述它的特征，请输入歌曲的 id 标题 或 别称（需bot支持，无需大小写） 进行猜歌（DX乐谱和标准乐谱视为两首歌）。猜歌时查歌等其他命令依然可用。')
    await guess_music_loop(bot, ev, state)


@sv.on_message()
async def guess_music_solve(bot, ev: CQEvent):
    gid = ev.group_id
    if gid not in guess_dict:
        return
    ans = ev.message.extract_plain_text().strip().lower()
    guess = guess_dict[gid]
    an = False
    if ans in music_aliases:
        result = music_aliases[ans]
        for i in result:
            if i == guess.music.title:
                an = True
                break
    if ans == guess.music.id or ans.lower() == guess.music.title.lower() or an:
        guess.is_end = True
        del guess_dict[gid]
        msg = f'''猜对了，答案是：
{random_music(guess.music)}'''
        await bot.finish(ev, msg, at_sender=True)


config_json = os.path.join(os.path.dirname(__file__), 'config.json')
if not os.path.exists('config.json'):
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump({'enable': [], 'disable': []}, f)
config: Dict[str, List[int]] = json.load(open(config_json, 'r', encoding='utf-8'))


def change(gid: int, set: bool):
    if set:
        if gid not in config['enable']:
            config['enable'].append(gid)
        if gid in config['disable']:
            config['disable'].remove(gid)
    else:
        if gid not in config['disable']:
            config['disable'].append(gid)
        if gid in config['enable']:
            config['enable'].remove(gid)
    try:
        with open(config_json, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=True, indent=4)
    except:
        traceback.print_exc()


@sv.on_fullmatch('开启mai猜歌')
async def guess_on(bot, ev: CQEvent):
    gid = ev.group_id
    is_ad = priv.check_priv(ev, priv.ADMIN)
    if not is_ad:
        await bot.finish(ev, '仅允许管理员开启')
    if gid in config['enable']:
        await bot.send(ev, '该群已开启猜歌功能')
    else:
        change(gid, True)
        await bot.send(ev, '已开启该群猜歌功能')


@sv.on_fullmatch('关闭mai猜歌')
async def guess_on(bot, ev: CQEvent):
    gid = ev.group_id
    is_ad = priv.check_priv(ev, priv.ADMIN)
    if not is_ad:
        await bot.finish(ev, '仅允许管理员关闭')
    if gid in config['disable']:
        await bot.send(ev, '该群已关闭猜歌功能')
    else:
        change(gid, False)
        if gid in guess_dict:
            del guess_dict[gid]
        await bot.send(ev, '已关闭该群猜歌功能')


arcades_json = os.path.join(os.path.dirname(__file__), 'arcades.json')
if not os.path.exists(arcades_json):
    raise '请安装arcades.json文件'
arcades: List[Dict] = json.load(open(arcades_json, 'r', encoding='utf-8'))


def modify(operate, arg, input_dict):
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


@sv.on_prefix('添加机厅')
async def add_arcade(bot, ev: CQEvent):
    args = ev.message.extract_plain_text().lower().strip().split()
    is_su = priv.check_priv(ev, priv.SUPERUSER)
    if not is_su:
        await bot.finish(ev, '仅允许主人添加机厅\n请使用 来杯咖啡+内容 联系主人')
    if len(args) == 1 and args[0] in ['帮助', 'help', '指令帮助']:
        await bot.send(ev, '添加机厅指令格式：添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ...', at_sender=True)
    elif len(args) > 1:
        if len(args) > 3 and not args[2].isdigit():
            await bot.send(ev, '格式错误：添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ...', at_sender=True)
        else:
            arcade_dict = {'name': args[0], 'location': args[1],
                           'num': int(args[2]) if len(args) > 2 else 1,
                           'alias': args[3:] if len(args) > 3 else [],
                           'group': [], 'person': 0,
                           'by': '', 'time': ''}
            await bot.send(ev, modify('add', None, arcade_dict), at_sender=True)
    else:
        await bot.send(ev, '格式错误：添加机厅 <名称> <位置> <机台数量> <别称1> <别称2> ...', at_sender=True)


@sv.on_prefix('删除机厅')
async def delele_arcade(bot, ev: CQEvent):
    args = ev.message.extract_plain_text().lower().strip().split()
    is_su = priv.check_priv(ev, priv.SUPERUSER)
    if not is_su:
        await bot.finish(ev, '仅允许主人删除机厅\n请使用 来杯咖啡+内容 联系主人')
    if len(args) == 1:
        await bot.send(ev, modify('delete', None, {'name': args[0]}), at_sender=True)
    else:
        await bot.send(ev, '格式错误：删除机厅 <名称>', at_sender=True)


@sv.on_prefix('修改机厅')
async def modify_arcade(bot, ev: CQEvent):
    args = ev.message.extract_plain_text().lower().strip().split()
    is_ad = priv.check_priv(ev, priv.ADMIN)
    if not is_ad:
        await bot.finish(ev, '仅允许管理员修改机厅信息')
    if len(args) == 1 and args[0] in ['帮助', 'help', '指令帮助']:
        await bot.send(ev, '修改机厅指令格式：修改机厅 <名称> [数量/别称] [<数量>/添加/删除] <别称1> <别称2> ...', at_sender=True)
    elif args[1] == '数量':
        if len(args) == 3 and args[2].isdigit():
            await bot.send(ev, modify('modify', 'num', {'name': args[0], 'num': args[2]}), at_sender=True)
        else:
            await bot.send(ev, '格式错误：修改机厅 <名称> 数量 <数量>', at_sender=True)
    elif args[1] == '别称':
        if args[2] in ['添加', '删除'] and len(args) > 3:
            await bot.send(ev, modify('modify', 'alias_delete' if args[2] == '删除' else 'alias_add',
                                      {'name': args[0], 'alias': args[3] if args[2] == '删除' else args[3:]}), at_sender=True)
        else:
            await bot.send(ev, '格式错误：修改机厅 <名称> 别称 [添加/删除] <别称1> <别称2> ...', at_sender=True)
    else:
        await bot.send(ev, '格式错误：修改机厅 <名称> [数量/别称] [<数量>/添加/删除] <别称1> <别称2> ...', at_sender=True)


@sv.on_prefix('订阅机厅')
async def subscribe_arcade(bot, ev: CQEvent):
    gid = ev.group_id
    args = ev.message.extract_plain_text().lower().strip().split()
    is_ad = priv.check_priv(ev, priv.ADMIN)
    if not is_ad:
        await bot.finish(ev, '仅允许管理员订阅')
    for a in arcades:
        if gid in a['group']:
            await bot.finish(ev, f'该群已订阅机厅：{a["name"]}', at_sender=True)
    if len(args) == 1:
        await bot.send(ev, modify('modify', 'subscribe', {'name': args[0], 'gid': gid}), at_sender=True)
    else:
        await bot.send(ev, '格式错误：订阅机厅 <名称>', at_sender=True)


@sv.on_fullmatch('查看订阅')
async def check_subscribe(bot, ev: CQEvent):
    gid = ev.group_id
    result = None
    for a in arcades:
        if gid in a['group']:
            result = a
            break
    if result:
        await bot.send(ev, f'''群{gid}订阅机厅信息如下：
{result["name"]} {result["location"]} 机台数量 {result["num"]} {"别称：" if len(result["alias"]) > 0 else ""}{"/".join(result["alias"])}'''.strip(), at_sender=True)
    else:
        await bot.send(ev, '该群未订阅任何机厅', at_sender=True)


@sv.on_fullmatch(['取消订阅', '取消订阅机厅'])
async def unsubscribe_arcade(bot, ev: CQEvent):
    gid = ev.group_id
    is_ad = priv.check_priv(ev, priv.ADMIN)
    if not is_ad:
        await bot.finish(ev, '仅允许管理员订阅')
    result = None
    for a in arcades:
        if gid in a['group']:
            result = a
            break
    if result:
        await bot.send(ev, modify('modify', 'unsubscribe', {'name': result['name'], 'gid': gid}), at_sender=True)
    else:
        await bot.send(ev, '该群未订阅任何机厅，请使用 订阅机厅 <名称> 指令订阅机厅', at_sender=True)


@sv.on_prefix(['查找机厅', '查询机厅', '机厅查找', '机厅查询'])
async def search_arcade(bot, ev: CQEvent):
    args = ev.message.extract_plain_text().lower().strip().split()
    if len(args) == 1:
        result = []
        for a in arcades:
            match = False
            if args[0] in a['name']:
                match = True
            if args[0] in a['location']:
                match = True
            for alias in a['alias']:
                if args[0] in alias:
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
            await bot.send(ev, f'[CQ:image,file=base64://{image_to_base64(text_to_image(msg.strip())).decode()}]', at_sender=True)
    else:
        await bot.send(ev, '格式错误：查找机厅 <关键词>', at_sender=True)


@sv.on_rex(r'^(.+)?\s?(设置|设定|＝|=|增加|添加|加|＋|\+|减少|降低|减|－|-)\s?([0-9]+)(人|卡)?$')
async def arcade_person(bot, ev: CQEvent):
    match = ev['match']
    gid = ev.group_id
    sender = ev.sender["nickname"]
    if not match.group(3).isdigit():
        await bot.finish(ev, '请输入正确的数字', at_sender=True)
    result = None
    empty_name = False
    if match.group(1):
        if '人数' in match.group(1) or '卡' in match.group(1):
            search_key = match.group(1)[:-2] if '人数' in match.group(1) else match.group(1)[:-1]
            if search_key:
                for a in arcades:
                    if search_key.lower() == a['name']:
                        result = a
                        break
                    if search_key.lower() in a['alias']:
                        result = a
                        break
                if not result:
                    await bot.finish(ev, '没有这样的机厅哦', at_sender=True)
            else: empty_name = True
        else:
            for a in arcades:
                if match.group(1).lower() == a['name']:
                    result = a
                    break
                if match.group(1).lower() in a['alias']:
                    result = a
                    break
            if not result:
                return
    else:
        return
    if not result or empty_name:
        for a in arcades:
            if gid in a['group']:
                result = a
                break
    if result:
        msg = ''
        if match.group(2) in ['设置', '设定', '＝', '=']:
            msg = modify('modify', 'person_set', {'name': result['name'], 'person': match.group(3),
                                                               'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                               'by': sender})
            await bot.send(ev, msg.strip(), at_sender=True)
        elif match.group(2) in ['增加', '添加', '加', '＋', '+']:
            msg = modify('modify', 'person_add', {'name': result['name'], 'person': match.group(3),
                                                               'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                               'by': sender})
            await bot.send(ev, msg.strip(), at_sender=True)
        elif match.group(2) in ['减少', '降低', '减', '－', '-']:
            msg = modify('modify', 'person_minus', {'name': result['name'], 'person': match.group(3),
                                                                 'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                                 'by': sender})
            await bot.send(ev, msg.strip(), at_sender=True)
        if msg and '一次最多改变' in msg:
            await hoshino.util.silence(ev, 5 * 60)
            await bot.send(ev, '请勿乱玩bot，恼！', at_sender=True)
    else:
        await bot.send(ev, '该群未订阅机厅，请发送 订阅机厅 <名称> 指令订阅机厅', at_sender=True)



@sv.on_suffix(['有多少人', '有几人', '有几卡', '几人', '几卡'])
async def arcade_query_person(bot, ev: CQEvent):
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
            msg += f'机均{result["person"]/result["num"]:.2f}人\n'
        if result['by']:
            msg += f'由{result["by"]}更新于{result["time"]}'
        await bot.send(ev, msg.strip(), at_sender=True)
    else:
        await bot.send(ev, '该群未订阅任何机厅，请使用 订阅机厅 <名称> 指令订阅机厅', at_sender=True)
