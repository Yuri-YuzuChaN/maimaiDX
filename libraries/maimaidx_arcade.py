import json
import time
import traceback
from typing import Dict, List, Optional, overload

import aiohttp
from pydantic import BaseModel

from .. import arcades_json, loga
from .maimaidx_music import writefile


class Arcade(BaseModel):
    
    name: str
    location: str
    province: str
    mall: str
    num: int
    id: str
    alias: List[str]
    group: List[int]
    person: int
    by: str
    time: str


class ArcadeList(List[Arcade]):

    async def save_arcade(self) -> bool:
        return await writefile(arcades_json, [_.model_dump() for _ in self])
    
    @overload
    def search_name(self, *, name: Optional[str] = ...) -> List[Arcade]:
        """查询所有机厅"""
    @overload
    def search_name(self, *, alias: Optional[str] = ...) -> List[Arcade]:
        """只查询别名机厅"""
    @overload
    def search_name(self, *, id: Optional[str] = ...) -> List[Arcade]:
        """指定ID查询机厅"""
    def search_name(self,
                    *,
                    name: Optional[str] = ...,
                    alias: Optional[str] = ...,
                    id: Optional[str] = ...) -> List[Arcade]:
        arcade_list = []
        for arcade in self:
            if name:
                if name in arcade.name:
                    arcade_list.append(arcade)
                elif name in arcade.location:
                    arcade_list.append(arcade)
                if name in arcade.alias:
                    arcade_list.append(arcade)
            if alias and alias in arcade.alias:
                arcade_list.append(arcade)
            if id and id == arcade.id:
                arcade_list.append(arcade)
        
        return arcade_list

    def add_subscribe_arcade(self, group_id: int, arcadeName: str) -> bool:
        """添加订阅机厅"""
        for arcade in self:
            if arcadeName == arcade.name:
                arcade.group.append(group_id)
                return True
        return False
    
    def add_arcade_alias(self, arcadeName: str, arcadeAlias: str) -> bool:
        """添加机厅别名"""
        for arcade in self:
            if arcadeName == arcade.name:
                arcade.alias.append(arcadeAlias)
                return True
        return False
    
    def group_in_arcade(self, group_id: int, arcadeName: str) -> bool:
        """是否已订阅该机厅"""
        for arcade in self:
            if arcadeName == arcade.name:
                if group_id in arcade.group:
                    return True
        return False
    
    def group_subscribe_arcade(self, group_id: int) -> List[Arcade]:
        """已订阅机厅"""
        arcade_list = []
        for arcade in self:
            if group_id in arcade.group:
                arcade_list.append(arcade)
        return arcade_list

    def del_subscribe_arcade(self, group_id: int, arcadeName: str) -> bool:
        """删除订阅机厅"""
        for arcade in self:
            if arcadeName == arcade.name:
                arcade.group.remove(group_id)
                return True
        return False

    @classmethod
    def arcade_to_msg(cls, arcade_list: List[Arcade]) -> List[str]:
        """机厅人数格式化"""
        result = []
        for arcade in arcade_list:
            msg = f'''{arcade.name}
    - 当前 {arcade.person} 人\n'''
            if arcade.num > 1:
                msg += f'    - 平均 {arcade.person / arcade.num:.2f} 人\n'
            if arcade.by:
                msg += f'    - 由 {arcade.by} 更新于 {arcade.time}'
            result.append(msg.strip())
        return result


class ArcadeData:
    
    total: Optional[ArcadeList]
    
    def __init__(self) -> None: 
        if arcades_json.exists():
            with open(arcades_json, 'w', encoding='utf8') as f:
                json.dump([], f)
        self.arcades: List[Dict] = json.load(open(arcades_json, 'r', encoding='utf-8'))
    
    async def getArcade(self):
        self.total = await download_arcade_info()


arcade = ArcadeData()


async def download_arcade_info(save: bool = True) -> ArcadeList:
    try:
        async with aiohttp.request('GET', 'http://wc.wahlap.net/maidx/rest/location', timeout=aiohttp.ClientTimeout(total=30)) as req:
            if req.status == 200:
                data = await req.json()
            else:
                loga.error('获取机厅信息失败')
        current_names = [c_a['name'] for c_a in arcade.arcades]
        arcadelist = ArcadeList(data)
        for num in range(len(data)):
            if data[num]['arcadeName'] not in current_names:
                arcade_dict = {
                    'name': data[num]['arcadeName'],
                    'location': data[num]['address'],
                    'province': data[num]['province'],
                    'mall': data[num]['mall'],
                    'num': data[num]['machineCount'],
                    'id': data[num]['id'],
                    'alias': [], 'group': [],
                    'person': 0, 'by': '', 'time': ''
                }
                arcade.arcades.append(arcade_dict)
            else:
                arcade_dict = arcade.arcades[current_names.index(data[num]['arcadeName'])]
                arcade_dict['location'] = data[num]['address']
                arcade_dict['province'] = data[num]['province']
                arcade_dict['mall'] = data[num]['mall']
                arcade_dict['num'] = data[num]['machineCount']
                arcade_dict['id'] = data[num]['id']
            arcadelist[num] = Arcade(**arcade_dict)
        if save:
            await writefile(arcades_json, arcade.arcades)
    except Exception:
        loga.error(f'Error: {traceback.format_exc()}')
        loga.error('获取机厅信息失败')
    return arcadelist


@overload
async def modify(*, group_id: Optional[int] = ..., arcadeName: Optional[str] = ..., sub: bool = False) -> str:
    """订阅机厅，`sub` 等于True时为订阅，False为取消订阅"""
@overload
async def modify(*, arcadeList: Optional[List[Arcade]] = ..., userName: Optional[str] = ..., value: Optional[str] = ..., person: Optional[int] = ...) -> str:
    """变更机厅人数"""
@overload
async def modify(*, arcadeName: Optional[str] = ..., aliasName: Optional[str] = ...) -> str:
    """变更机厅别名"""
async def modify(*, group_id: Optional[int] = 0,
                arcadeList: Optional[List[Arcade]] = [],
                arcadeName: Optional[str] = None,
                aliasName: Optional[str] = None,
                userName: Optional[str] = None,
                value: Optional[str] = None,
                person: Optional[int] = 0,
                sub: bool = False) -> str:
    
    change = False
    msg = ''
    if group_id and arcadeName:
        if sub:
            arcade.total.add_subscribe_arcade(group_id, arcadeName)
            msg = f'群：{group_id} 已添加订阅机厅：{arcadeName}'
        else:
            arcade.total.del_subscribe_arcade(group_id, arcadeName)
            msg = f'群：{group_id} 已取消订阅机厅：{arcadeName}'
        change = True
    elif arcadeList and userName and value:
        if len(arcadeList) == 1:
            _arcade = arcadeList[0]
            if value in ['+', '＋', '增加', '添加', '加']:
                _arcade.person += person
            elif value in ['-', '－', '减少', '降低', '减' ]:
                _arcade.person -= person
            elif value in ['=', '＝', '设置', '设定']:
                _arcade.person = person
            _arcade.by = userName
            _arcade.time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            change = True
            msg = f'机厅：{_arcade.name}\n当前人数：{_arcade.person}\n变更时间：{_arcade.time}'
        elif len(arcadeList) > 1:
            msg = '找到多个机厅，请使用id变更人数\n' + '\n'.join([ f'{_.id}：{_.name}' for _ in arcadeList ])
        else:
            msg = '没有找到指定机厅'
    elif arcadeName and aliasName:
        arcade_list = arcade.total.search_name(name=arcadeName)
        if arcade_list:
            _arcade = arcade_list[0]
            if aliasName not in _arcade.alias:
                _arcade.alias.append(aliasName)
                msg = f'机厅：{_arcade.name}\n已添加别名：{aliasName}'
                change = True
            else:
                msg = f'机厅：{_arcade.name}\n已拥有别名：{aliasName}\n请勿重复添加'
        else:
            msg = f'未找到机厅：{arcadeName}'
    if change:
        await arcade.total.save_arcade()
    return msg