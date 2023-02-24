import os
from quart import Blueprint, render_template, jsonify

from .libraries.maimaidx_project import *
from .libraries.maimaidx_api_data import *

mp = Blueprint('maimaiPage', __name__,
               url_prefix='/mai',
               template_folder='page',
               static_url_path='/statics',
               static_folder='mai')


@mp.route('/vote', methods=['GET'])
async def aliases_vote():
    return await render_template('index.html', static_url_path=mp.static_url_path, url_prefix=mp.url_prefix)


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
        b64image = (await draw_music_info(mai.total_list.by_id(d['ID']))).data['file']
        d['image'] = b64image.replace('base64://', 'data:image/png;base64,')
        vote_data.append(d)
    return jsonify({'result': vote_data})
