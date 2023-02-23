import os
from quart import Blueprint, render_template, jsonify

from .libraries.maimaidx_project import *
from .libraries.maimaidx_api_data import *

mp = Blueprint('maimaiPage', __name__,
               url_prefix='/mai',
               template_folder='page',
               static_folder='page')


async def draw_music_info(music: MusicList):
    im = Image.new('RGBA', (800, 1000))
    genre = category[music['basic_info']['genre']]

    music_bg = Image.open(os.path.join(newdir, 'music_bg.png')).convert('RGBA')
    cover = Image.open(await download_music_pictrue(music['id'])).convert('RGBA').resize((500, 500))
    anime = Image.open(os.path.join(newdir, f'{genre}.png')).convert('RGBA')
    anime_bg = Image.open(os.path.join(newdir, f'{genre}_bg.png')).convert('RGBA')
    music_title = Image.open(os.path.join(newdir, 'music_title.png')).convert('RGBA')
    diff = Image.open(os.path.join(newdir, 'diff.png')).convert('RGBA').resize((530, 79))
    line = Image.open(os.path.join(newdir, 'line.png')).convert('RGBA').resize((793, 14))
    verbpm = Image.open(os.path.join(newdir, 'ver&bpm.png')).convert('RGBA')

    im.alpha_composite(music_bg)
    im.alpha_composite(music_title, (52, 14))
    im.alpha_composite(anime_bg, (142, 175))
    im.alpha_composite(cover, (150, 183))
    im.alpha_composite(anime, (200, 135))
    im.alpha_composite(line, (5, 785))
    im.alpha_composite(diff, (135, 810))
    im.alpha_composite(verbpm, (50, 915))

    fontd = ImageDraw.Draw(im)

    font = DrawText(fontd, meiryo)
    font2 = DrawText(fontd, meiryob)

    font2.draw(270, 170, 28, music['id'], anchor='mm')
    font.draw_partial_opacity(400, 710, 20, music['basic_info']['artist'], 1, anchor='mm')
    font.draw_partial_opacity(400, 750, 38, music['title'], 1, anchor='mm')
    for n, i in enumerate(list(map(str, music["ds"]))):
        if n == 4:
            x = 615
            color = (195, 70, 231, 255)
        else:
            x = 190 + 105 * n
            color = (255, 255, 255, 255)
        font2.draw(x, 850, 28, i, color, anchor='mm')

    font.draw_partial_opacity(240, 940, 20, f'Ver:{music["basic_info"]["from"]}', 1, anchor='mm')
    font.draw_partial_opacity(580, 940, 20, f'BPM:{music["basic_info"]["bpm"]}', 1, anchor='mm')

    msg = image_to_base64(im)

    return msg


@mp.route('/vote', methods=['GET'])
async def aliases_vote():
    return await render_template('index.html')


@mp.route('/api/getVoteData', methods=['GET'])
async def get_vote_data():
    status = await get_alias('status')
    if not status:
        return {}, 200
    vote_data = []
    for tag in status:
        d = dict()
        d['ID'] = str(status[tag]['ID'])
        d['ApplyAlias'] = status[tag]['ApplyAlias']
        d['userNum'] = len(status[tag]['User'])
        d['index'] = tag
        music = mai.total_list.by_id(d['ID'])
        d['title'] = music.title
        d['image'] = (await draw_music_info(mai.total_list.by_id(d['ID']))).replace('base64://', 'data:image/png;base64,')
        vote_data.append(d)
    return jsonify({'result': vote_data})
