import json
from io import BytesIO
from pathlib import Path
from typing import Any, List, Optional, Union

from aiohttp import ClientSession, ClientTimeout

from .. import config_json, coverdir
from .maimaidx_error import *


class MaimaiAPI:
    
    MaiAPI = 'https://www.diving-fish.com/api/maimaidxprober'
    MaiCover = 'https://www.diving-fish.com/covers'
    MaiAliasAPI = 'https://api.yuzuchan.moe/maimaidx'
    QQAPI = 'http://q1.qlogo.cn/g'
    
    def __init__(self) -> None:
        self.token = self.load_token()
        self.headers = {'developer-token': self.token}
    
    def load_token(self) -> str:
        return json.load(open(config_json, 'r', encoding='utf-8'))['token']
    
    async def _request(self, method: str, url: str, **kwargs) -> Any:
        session = ClientSession(timeout=ClientTimeout(total=30))
        res = await session.request(method, url, **kwargs)

        data = None
        
        if self.MaiAPI in url:
            if res.status == 200:
                data = await res.json()
            elif res.status == 400:
                raise UserNotFoundError
            elif res.status == 403:
                raise UserDisabledQueryError
            else:
                raise UnknownError
        elif self.MaiAliasAPI in url:
            if res.status == 200:
                data = (await res.json())['content']
            elif res.status == 400:
                raise EnterError
            elif res.status == 500:
                raise ServerError
            else:
                raise UnknownError
        elif self.QQAPI in url:
            if res.status == 200:
                data = await res.read()
            else:
                raise
        await session.close()
        return data
    
    async def music_data(self):
        """获取曲目数据"""
        return await self._request('GET', self.MaiAPI + '/music_data')
    
    async def chart_stats(self):
        """获取单曲数据"""
        return await self._request('GET', self.MaiAPI + '/chart_stats')
    
    async def query_user(self, project: str, *, qqid: Optional[int] = None, username: Optional[str] = None, version: Optional[List[str]] = None):
        """
        请求用户数据
        
        - `project`: 查询的功能
            - `player`: 查询用户b50
            - `plate`: 按版本查询用户游玩成绩
        - `qqid`: 用户QQ
        - `username`: 查分器用户名
        """
        json = {}
        if qqid:
            json['qq'] = qqid
        if username:
            json['username'] = username
        if version:
            json['version'] = version
        if project == 'player':
            json['b50'] = True
        return await self._request('POST', self.MaiAPI + f'/query/{project}', json=json)
    
    async def query_user_dev(self, *, qqid: Optional[int] = None, username: Optional[str] = None):
        """
        使用开发者接口获取用户数据，请确保拥有和输入了开发者 `token`
        
        - `qqid`: 用户QQ
        - `username`: 查分器用户名
        """
        params = {}
        if qqid:
            params['qq'] = qqid
        if username:
            params['username'] = username
        return await self._request('GET', self.MaiAPI + f'/dev/player/records', headers=self.headers, params=params)

    async def query_user_dev2(self, *, qqid: Optional[int] = None, username: Optional[str] = None, music_id: Union[str, List[Union[int, str]]]):
        """
        使用开发者接口获取用户指定曲目数据，请确保拥有和输入了开发者 `token`

        - `qqid`: 用户QQ
        - `username`: 查分器用户名
        - `music_id`: 曲目id，可以为单个ID或者列表
        """
        json = {}
        if qqid:
            json['qq'] = qqid
        if username:
            json['username'] = username
        json['music_id'] = music_id
        return await self._request('POST', self.MaiAPI + f'/dev/player/record', headers=self.headers, json=json)

    async def rating_ranking(self):
        """获取查分器排行榜"""
        return await self._request('GET', self.MaiAPI + f'/rating_ranking')
        
    async def get_alias(self):
        """获取所有别名"""
        return await self._request('GET', self.MaiAliasAPI + '/maimaidxalias')
    
    async def get_songs(self, name: str):
        """使用别名查询曲目"""
        return await self._request('GET', self.MaiAliasAPI + '/getsongs', params={'name': name})
    
    async def get_songs_alias(self, song_id: int):
        """使用曲目 `id` 查询别名"""
        return await self._request('GET', self.MaiAliasAPI + '/getsongsalias', params={'song_id': song_id})
    
    async def get_alias_status(self):
        """获取当前正在进行的别名投票"""
        return await self._request('GET', self.MaiAliasAPI + '/getaliasstatus')
    
    async def get_alias_end(self):
        """获取五分钟内结束的别名投票"""
        return await self._request('GET', self.MaiAliasAPI + '/getaliasend')
    
    async def transfer_music(self):
        """中转查分器曲目数据"""
        return await self._request('GET', self.MaiAliasAPI + '/maimaidxmusic')
    
    async def transfer_chart(self):
        """中转查分器单曲数据"""
        return await self._request('GET', self.MaiAliasAPI + '/maimaidxchartstats')
    
    async def post_alias(self, id: int, aliasname: str, user_id: int):
        """
        提交别名申请
        
        - `id`: 曲目 `id`
        - `aliasname`: 别名
        - `user_id`: 提交的用户
        """
        json = {
            'SongID': id,
            'ApplyAlias': aliasname,
            'ApplyUID': user_id
        }
        return await self._request('POST', self.MaiAliasAPI + '/applyalias', json=json)
    
    async def post_agree_user(self, tag: str, user_id: int):
        """
        提交同意投票
        
        - `tag`: 标签
        - `user_id`: 同意投票的用户
        """
        json = {
            'Tag': tag,
            'AgreeUser': user_id
        }
        return await self._request('POST', self.MaiAliasAPI + '/agreeuser', json=json)

    async def download_music_pictrue(self, song_id: Union[int, str]) -> Union[Path, BytesIO]:
        try:
            if (file := coverdir / f'{song_id}.png').exists():
                return file
            song_id = int(song_id)
            if song_id > 100000:
                song_id -= 100000
                if (file := coverdir / f'{song_id}.png').exists():
                    return file
            if 1000 < song_id < 10000 or 10000 < song_id <= 11000:
                for _id in [song_id + 10000, song_id - 10000]:
                    if (file := coverdir / f'{_id}.png').exists():
                        return file
            pic = await self._request('GET', self.MaiCover + f'/{song_id:05d}.png')
            return BytesIO(pic)
        except CoverError:
            return coverdir / '11000.png'
        except Exception:
            return coverdir / '11000.png'

    async def qqlogo(self, qqid: int) -> bytes:
        params = {
            'b': 'qq',
            'nk': qqid,
            's': 100
        }
        return await self._request('GET', self.QQAPI, params=params)


maiApi = MaimaiAPI()