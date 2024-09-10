import re
from re import Match
from typing import List

from nonebot import NoneBot

from hoshino.typing import CQEvent, MessageSegment

from .. import SONGS_PER_PAGE, diffs, sv
from ..libraries.image import image_to_base64, text_to_image
from ..libraries.maimaidx_api_data import maiApi
from ..libraries.maimaidx_model import Alias
from ..libraries.maimaidx_music import guess, mai
from ..libraries.maimaidx_music_info import draw_music_info

search_music        = sv.on_prefix(['查歌', 'search'])
search_base         = sv.on_prefix(['定数查歌', 'search base'])
search_bpm          = sv.on_prefix(['bpm查歌', 'search bpm'])
search_artist       = sv.on_prefix(['曲师查歌', 'search artist'])
search_charter      = sv.on_prefix(['谱师查歌', 'search charter'])
search_alias_song   = sv.on_suffix(('是什么歌', '是啥歌'))
query_chart         = sv.on_rex(re.compile(r'^id\s?([0-9]+)$', re.IGNORECASE))


def song_level(ds1: float, ds2: float) -> list:
    result = []
    music_data = mai.total_list.filter(ds=(ds1, ds2))
    music_data.sort(key=lambda x: int(x.id))
    for music in music_data:
        for i in music.diff:
            result.append((music.id, music.title, music.ds[i], diffs[i], music.level[i]))
    return result


@search_music
async def _(bot: NoneBot, ev: CQEvent):
    name: str = ev.message.extract_plain_text().strip()
    if not name:
        return
    result = mai.total_list.filter(title_search=name)
    if len(result) == 0:
        await bot.send(ev, '没有找到这样的乐曲。\n※ 如果是别名请使用「xxx是什么歌」指令来查询哦。', at_sender=True)
    elif len(result) == 1:
        msg = await draw_music_info(result.random(), ev.user_id)
        await bot.send(ev, msg)
    elif len(result) < 50:
        search_result = ''
        result.sort(key=lambda x: int(x.id))
        for music in result:
            search_result += f'{music.id}. {music.title}\n'
        await bot.send(ev, search_result.strip() + '\n※ 请使用「id xxxxx」查询指定曲目', at_sender=True)
    else:
        await bot.send(ev, f'结果过多（{len(result)} 条），请缩小查询范围。', at_sender=True)


@search_base
async def _(bot: NoneBot, ev: CQEvent):
    args = ev.message.extract_plain_text().strip().split()
    if len(args) > 3 or len(args) == 0:
        await bot.finish(ev, '命令格式为\n定数查歌 <定数> [页数]\n定数查歌 <定数下限> <定数上限> [页数]', at_sender=True)
    page = 1
    if len(args) == 1:
        result = song_level(float(args[0]), float(args[0]))
    elif len(args) == 2:
        try:
            result = song_level(float(args[0]), float(args[1]))
        except:
            page = int(args[1]) if args[1].isdigit() else 1
            result = song_level(float(args[0]), float(args[0]))
    elif len(args) == 3:
        try:
            page = int(args[2]) if args[2].isdigit() else 1
            result = song_level(float(args[0]), float(args[1]))
        except:
            page = int(args[2]) if args[2].isdigit() else 1
            result = song_level(float(args[0]), float(args[0]))
    else:
        result = song_level(float(args[0]), float(args[1]))
        page = int(args[2]) if args[2].isdigit() else 1
    if not result:
        await bot.finish(ev, f'没有找到这样的乐曲。', at_sender=True)
    msg = ''
    page = max(min(page, len(result) // SONGS_PER_PAGE + 1), 1)
    for i, r in enumerate(result):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            msg += f'{r[0]}. {r[1]} {r[3]} {r[4]}({r[2]})\n'
    msg += f'第{page}页，共{len(result) // SONGS_PER_PAGE + 1}页'
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg.strip()))), at_sender=True)


@search_bpm
async def search_dx_song_bpm(bot: NoneBot, ev: CQEvent):
    if str(ev.group_id) in guess.Group:
        await bot.finish(ev, '本群正在猜歌，不要作弊哦~', at_sender=True)
    args = ev.message.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        music_data = mai.total_list.filter(bpm=int(args[0]))
    elif len(args) == 2:
        if (bpm := int(args[0])) > int(args[1]):
            page = int(args[1])
            music_data = mai.total_list.filter(bpm=bpm)
        else:
            music_data = mai.total_list.filter(bpm=(bpm, int(args[1])))
    elif len(args) == 3:
        music_data = mai.total_list.filter(bpm=(int(args[0]), int(args[1])))
        page = int(args[2])
    else:
        await bot.finish(ev, '命令格式为：\nbpm查歌 <bpm>\nbpm查歌 <bpm下限> <bpm上限> (<页数>)', at_sender=True)
    if not music_data:
        await bot.finish(ev, f'没有找到这样的乐曲。', at_sender=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(sorted(music_data, key=lambda i: int(i.basic_info.bpm))):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            msg += f'No.{i + 1} {m.id}. {m.title} bpm {m.basic_info.bpm}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg.strip()))), at_sender=True)


@search_artist
async def search_dx_song_artist(bot: NoneBot, ev: CQEvent):
    if str(ev.group_id) in guess.Group:
        await bot.finish(ev, '本群正在猜歌，不要作弊哦~', at_sender=True)
    args: List[str] = ev.message.extract_plain_text().strip().split()
    page = 1
    name = ''
    if len(args) == 1:
        name: str = args[0]
    elif len(args) == 2:
        name: str = args[0]
        if args[1].isdigit():
            page = int(args[1])
        else:
            await bot.finish(ev, '命令格式为：曲师查歌 <曲师名称> (<页数>)', at_sender=True)
    else:
        await bot.finish(ev, '命令格式为：曲师查歌 <曲师名称> (<页数>)', at_sender=True)
    if not name:
        return
    music_data = mai.total_list.filter(artist_search=name)
    if not music_data:
        await bot.finish(ev, f'没有找到这样的乐曲。', at_sender=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(music_data):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            msg += f'No.{i + 1} {m.id}. {m.title} {m.basic_info.artist}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg.strip()))), at_sender=True)


@search_charter
async def search_dx_song_charter(bot: NoneBot, ev: CQEvent):
    if str(ev.group_id) in guess.Group:
        await bot.finish(ev, '本群正在猜歌，不要作弊哦~', at_sender=True)
    args: List[str] = ev.message.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        name: str = args[0]
    elif len(args) == 2:
        name: str = args[0]
        if args[1].isdigit():
            page = int(args[1])
        else:
            await bot.finish(ev, '命令格式为：谱师查歌 <谱师名称> (<页数>)', at_sender=True)
    else:
        await bot.finish(ev, '命令格式为：谱师查歌 <谱师名称> (<页数>)', at_sender=True)
    if not name:
        return
    music_data = mai.total_list.filter(charter_search=name)
    if not music_data:
        await bot.finish(ev, f'没有找到这样的乐曲。', at_sender=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(music_data):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            diff_charter = zip([diffs[d] for d in m.diff], [m.charts[d].charter for d in m.diff])
            msg += f'No.{i + 1} {m.id}. {m.title} {" ".join([f"{d}/{c}" for d, c in diff_charter])}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await bot.send(ev, MessageSegment.image(image_to_base64(text_to_image(msg.strip()))), at_sender=True)


@search_alias_song
async def _(bot: NoneBot, ev: CQEvent):
    name: str = ev.message.extract_plain_text().strip().lower()
    # 别名
    alias_data = mai.total_alias_list.by_alias(name)
    if not alias_data:
        obj = await maiApi.get_songs(name)
        if obj:
            if 'status' in obj and obj['status']:
                msg = f'未找到别名为「{name}」的歌曲，但找到与此相同别名的投票：\n'
                for _s in obj['status']:
                    msg += f'- {_s["Tag"]}\n    ID {_s["SongID"]}: {name}\n'
                msg += f'※ 可以使用指令「同意别名 {_s["Tag"]}」进行投票'
                await bot.finish(ev, msg.strip(), at_sender=True)
            else:
                alias_data = [Alias(**_a) for _a in obj]
    if alias_data:
        if len(alias_data) != 1:
            msg = f'找到{len(alias_data)}个相同别名的曲目：\n'
            for songs in alias_data:
                msg += f'{songs.SongID}：{songs.Name}\n'
            msg += '※ 请使用「id xxxxx」查询指定曲目'
            await bot.finish(ev, msg.strip(), at_sender=True)
        else:
            music = mai.total_list.by_id(str(alias_data[0].SongID))
            if music:
                msg = '您要找的是不是：' + (await draw_music_info(music, ev.user_id))
            else:
                msg = f'未找到别名为「{name}」的歌曲\n※ 可以使用「添加别名」指令给该乐曲添加别名\n※ 如果是歌名的一部分，请使用「查歌」指令查询哦。'
            await bot.finish(ev, msg, at_sender=True)
    # id
    if name.isdigit() and (music := mai.total_list.by_id(name)):
        await bot.finish(ev, '您要找的是不是：' + (await draw_music_info(music, ev.user_id)), at_sender=True)
    if search_id := re.search(r'^id([0-9]*)$', name, re.IGNORECASE):
        music = music = mai.total_list.by_id(search_id.group(1))
        await bot.finish(ev, '您要找的是不是：' + (await draw_music_info(music, ev.user_id)), at_sender=True)
    # 标题
    result = mai.total_list.filter(title_search=name)
    if len(result) == 0:
        await bot.finish(ev, f'未找到别名为「{name}」的歌曲\n※ 可以使用「添加别名」指令给该乐曲添加别名\n※ 如果是歌名的一部分，请使用「查歌」指令查询哦。', at_sender=True)
    elif len(result) == 1:
        msg = await draw_music_info(result.random(), ev.user_id)
        await bot.finish(ev, '您要找的是不是：' + await draw_music_info(result.random(), ev.user_id), at_sender=True)
    elif len(result) < 50:
        msg = f'未找到别名为「{name}」的歌曲，但找到{len(result)}个相似标题的曲目：\n'
        for music in sorted(result, key=lambda x: int(x.id)):
            msg += f'{music.id}. {music.title}\n'
        msg += '※ 请使用「id xxxxx」查询指定曲目'
        await bot.finish(ev, msg.strip(), at_sender=True)
    else:
        await bot.finish(ev, f'结果过多（{len(result)} 条），请缩小查询范围。', at_sender=True)


@query_chart
async def _(bot: NoneBot, ev: CQEvent):
    match: Match[str] = ev['match']
    id = match.group(1)
    music = mai.total_list.by_id(id)
    if not music:
        msg = f'未找到ID为「{id}」的乐曲'
    else:
        msg = await draw_music_info(music, ev.user_id)
    await bot.send(ev, msg)