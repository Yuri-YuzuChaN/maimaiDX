from nonebot.typing import State_T
from hoshino import Service, priv
from hoshino.typing import CQEvent
from collections import defaultdict
import os, re, asyncio, json, traceback

from .libraries.maimai_best_40 import generate
from .libraries.image import *
from .libraries.maimaidx_music import *
from .libraries.tool import hash, search_dict
from .libraries.maimaidx_guess import GuessObject

sv_help = '''
可用命令如下：
今日mai,今日舞萌,今日运势 查看今天的舞萌运势
XXXmaimaiXXX什么 随机一首歌
随个[dx/标准][绿黄红紫白]<难度> 随机一首指定条件的乐曲
查歌<乐曲标题的一部分> 查询符合条件的乐曲
[绿黄红紫白]id <歌曲编号> 查询乐曲信息或谱面信息
<歌曲别名>是什么歌 查询乐曲别名对应的乐曲
定数查歌 <定数>  查询定数对应的乐曲
定数查歌 <定数下限> <定数上限>
分数线 <难度+歌曲id> <分数线> 详情请输入“分数线 帮助”查看
开启/关闭mai猜歌 开关猜歌功能
猜歌 顾名思义，识别id，歌名和别称
b40 <名字> 查B40'''

sv = Service('maimaiDX', manage_priv=priv.ADMIN, enable_on_default=False, help_=sv_help)

static = os.path.join(os.path.dirname(__file__), 'static')

def random_music(music: Music) -> str:
    msg = f'''{music.id}. {music.title}
[CQ:image,file=https://www.diving-fish.com/covers/{music.id}.jpg]
{'/'.join(music.level)}'''
    return msg

def song_level(ds1: float, ds2: float = None) -> list:
    result = []
    diff_label = ['Bas', 'Adv', 'Exp', 'Mst', 'ReM']
    if ds2 is not None:
        music_data = total_list.filter(ds=(ds1, ds2))
    else:
        music_data = total_list.filter(ds=ds1)
    for music in sorted(music_data, key = lambda i: int(i['id'])):
        for i in music.diff:
            result.append((music['id'], music['title'], music['ds'][i], diff_label[i], music['level'][i]))
    return result

@sv.on_prefix('定数查歌')
async def search_dx_song_level(bot, ev:CQEvent):
    args = ev.message.extract_plain_text().strip().split()
    if len(args) > 2 or len(args) == 0:
        await bot.finish(ev, '命令格式为\n定数查歌 <定数>\n定数查歌 <定数下限> <定数上限>', at_sender=True)
    if len(args) == 1:
        result = song_level(float(args[0]))
    else:
        result = song_level(float(args[0]), float(args[1]))
    if len(result) > 50:
        await bot.finish(ev, f'结果过多（{len(result)} 条），请缩小搜索范围', at_sender=True)
    msg = ''
    for i in result:
        msg += f'{i[0]}. {i[1]} {i[3]} {i[4]}({i[2]})\n'
    await bot.finish(ev, msg.strip(), at_sender=True)

@sv.on_rex(r'^随个((?:dx|sd|标准))?([绿黄红紫白]?)([0-9]+\+?)')
async def random_song(bot, ev:CQEvent):
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
async def random_day_song(bot, ev:CQEvent):
    await bot.send(ev, random_music(total_list.random()))

@sv.on_prefix('查歌')
async def search_song(bot, ev:CQEvent):
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

@sv.on_rex(r'^([绿黄红紫白]?)id ([0-9]+)')
async def query_chart(bot, ev:CQEvent):
    match = ev['match']
    level_labels = ['绿', '黄', '红', '紫', '白']
    if match.group(1) != '':
        try:
            level_index = level_labels.index(match.group(1))
            level_name = ['Basic', 'Advanced', 'Expert', 'Master', 'Re: MASTER']
            name = match.group(2)
            music = total_list.by_id(name)
            chart = music['charts'][level_index]
            ds = music['ds'][level_index]
            level = music['level'][level_index]
            if len(chart['notes']) == 4:
                result = f'''{level_name[level_index]} {level}({ds})
TAP: {chart['notes'][0]}
HOLD: {chart['notes'][1]}
SLIDE: {chart['notes'][2]}
BREAK: {chart['notes'][3]}
谱师: {chart['charter']}'''
            else:
                result = f'''{level_name[level_index]} {level}({ds})
TAP: {chart['notes'][0]}
HOLD: {chart['notes'][1]}
SLIDE: {chart['notes'][2]}
TOUCH: {chart['notes'][3]}
BREAK: {chart['notes'][4]}
谱师: {chart['charter']}'''

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
难度: {'/'.join(music['level'])}'''
            await bot.send(ev, msg, at_sender=True)
        except:
            await bot.send(ev, '未找到该乐曲', at_sender=True)

@sv.on_fullmatch(['今日mai', '今日舞萌', '今日运势'])
async def day_mai(bot, ev:CQEvent):
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
    msg += '千雪提醒您：打机时不要大力拍打或滑动哦\n今日推荐歌曲：'
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

@sv.on_suffix('是什么歌')
async def what_song(bot, ev:CQEvent):
    name = ev.message.extract_plain_text().strip()
    result = search_dict(music_aliases, name)
    if len(result) == 0:
        await bot.finish(ev, '未找到此歌曲\n舞萌 DX 歌曲别名收集计划：https://docs.qq.com/sheet/DQ0pvUHh6b1hjcGpl', at_sender=True)
    if len(result) == 1:
        music = total_list.by_title(result[0])
        await bot.send(ev, '您要找的是不是：' + random_music(music), at_sender=True)
    else:
        msg = '\n'.join(result)
        await bot.send(ev, f'您要找的可能是以下歌曲中的其中一首：\n{msg}', at_sender=True)

@sv.on_prefix('分数线')
async def quert_score(bot, ev:CQEvent):
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
    elif len(args) == 2:
        try:
            result = re.search(r'([绿黄红紫白])(id)?([0-9]+)', args[0])
            level_labels = ['绿', '黄', '红', '紫', '白']
            level_labels2 = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:MASTER']
            level_index = level_labels.index(result.group(1))
            chart_id = result.group(3)
            line = float(args[1])
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

@sv.on_prefix(['b40', 'B40'])
async def best_40(bot, ev:CQEvent):
    args = ev.message.extract_plain_text().strip()
    if not args:
        payload = {'qq': str(ev.user_id)}
    else:
        payload = {'username': args}
    img, success = await generate(payload)
    if success == 400:
        await bot.send(ev, '未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。', at_sender=True)
    elif success == 403:
        await bot.send(ev, '该用户禁止了其他人获取数据。', at_sender=True)
    else:
        await bot.send(ev, f'[CQ:image,file=base64://{image_to_base64(img).decode()}]', at_sender=True)

guess_dict: Dict[Tuple[str], GuessObject] = {}

async def guess_music_loop(bot, ev:CQEvent, state: State_T):
    await asyncio.sleep(8)
    guess: GuessObject = state['guess_object']
    if guess.is_end:
        return
    cycle = state['cycle']
    if cycle < 6:
        await bot.send(ev, f'{cycle + 1}/7 这首歌{guess.guess_options[cycle]}')
    else:
        msg = f'''7/7 这首歌封面的一部分是：
[CQ:image,file=base64://{str(guess.b64image, encoding='utf-8')}]
答案将在30秒后揭晓'''
        await bot.send(ev, msg)
        await give_answer(bot, ev, state)
    state['cycle'] += 1
    await guess_music_loop(bot, ev, state)

async def give_answer(bot, ev:CQEvent, state: State_T):
    await asyncio.sleep(30)
    guess: GuessObject = state['guess_object']
    if guess.is_end:
        return
    msg = f'''答案是：{guess.music['id']}. {guess.music['title']}
[CQ:image,file=https://www.diving-fish.com/covers/{guess.music['id']}.jpg]'''
    del guess_dict[state['gid']]
    await bot.finish(ev, msg)

@sv.on_fullmatch('猜歌')
async def guess_music(bot, ev:CQEvent):
    gid = ev.group_id
    if gid not in config['enable']:
        await bot.finish(ev, '该群已关闭猜歌功能，开启请输入 开启mai猜歌')
    if gid in guess_dict:
        await bot.finish(ev, '当前已有正在进行的猜歌')

    guess = GuessObject()
    guess_dict[gid] = guess
    state: State_T = {'gid': gid, 'guess_object': guess, 'cycle': 0}
    await bot.send(ev, '我将从热门乐曲中选择一首歌，每隔8秒描述它的特征，请输入歌曲的 id 标题 或 别称（需bot支持，无需大小写）进行猜歌（DX乐谱和标准乐谱视为两首歌）。猜歌时查歌等其他命令依然可用。')
    await guess_music_loop(bot, ev, state)

@sv.on_message()
async def guess_music_solve(bot, ev:CQEvent):
    gid = ev.group_id
    if gid not in guess_dict:
        return
    ans = ev.message.extract_plain_text().strip()
    guess = guess_dict[gid]
    an = False
    result = search_dict(music_aliases, ans)
    for i in result:
        if i == guess.music['title']:
            an = True
            break
    if ans == guess.music['id'] or an:
        guess.is_end = True
        del guess_dict[gid]
        msg = f'''猜对了，答案是：
{guess.music['id']}. {guess.music['title']}
[CQ:image,file=https://www.diving-fish.com/covers/{guess.music['id']}.jpg]'''
        await bot.send(ev, msg, at_sender=True)

config_json = os.path.join(os.path.dirname(__file__), 'config.json')
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
async def guess_on(bot, ev:CQEvent):
    is_ad = priv.check_priv(ev, priv.ADMIN)
    if not is_ad:
        await bot.finish(ev, '仅允许管理员开启')
    if ev.group_id in config['enable']:
        await bot.send(ev, '该群已开启猜歌功能')
    else:
        change(ev.group_id, True)
        await bot.send(ev, '已开启该群猜歌功能')

@sv.on_fullmatch('关闭mai猜歌')
async def guess_on(bot, ev:CQEvent):
    is_ad = priv.check_priv(ev, priv.ADMIN)
    if not is_ad:
        await bot.finish(ev, '仅允许管理员关闭')
    if ev.group_id in config['disable']:
        await bot.send(ev, '该群已关闭猜歌功能')
    else:
        change(ev.group_id, False)
        await bot.send(ev, '已关闭该群猜歌功能')
