import os

import nonebot
from fastapi import Request, FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..libraries.maimaidx_api_data import get_alias
from ..libraries.maimaidx_music import mai
from ..libraries.maimaidx_project import draw_music_info

static_directory = os.path.dirname(__file__) + '/static'
template_directory = os.path.dirname(__file__) + '/templates'

app: FastAPI = nonebot.get_app()
app.mount('/static', StaticFiles(directory=static_directory), name='static')
templates = Jinja2Templates(directory=template_directory, auto_reload=True)


@app.get('/vote', response_class=HTMLResponse)
async def _(request: Request):
    return templates.TemplateResponse('index.html', context={'request': request})


@app.get('/api/getVoteData', response_class=JSONResponse)
async def _():
    status = await get_alias('status')
    if not status:
        return {}, 200
    vote_data = []
    for tag in status:
        d = dict()
        id_ = d['ID'] = str(status[tag]['ID'])
        d['ApplyAlias'] = status[tag]['ApplyAlias']
        d['userNum'] = len(status[tag]['User'])
        d['votes'] = status[tag]['votes']
        d['index'] = tag
        music = mai.total_list.by_id(id_)
        d['title'] = music.title
        d['image'] = f'/image/{id_}.png'
        vote_data.append(d)
    return {'result': vote_data}


@app.get('/image/{image_id}.png', response_class=StreamingResponse)  # 伪静态
async def _(image_id: str):
    image = await draw_music_info(mai.total_list.by_id(image_id))
    return StreamingResponse(image, media_type='image/png')
