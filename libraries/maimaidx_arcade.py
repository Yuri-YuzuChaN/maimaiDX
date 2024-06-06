import json
import time
import traceback
from typing import Dict, List, Optional, Union

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


    async def save_arcade(self):
        return await writefile(arcades_json, [_.model_dump() for _ in self])
    
    def search_name(self, name: str) -> List[Arcade]:
        """模糊查询机厅"""
        arcade_list = []
        for arcade in self:
            if name in arcade.name:
                arcade_list.append(arcade)
            elif name in arcade.location:
                arcade_list.append(arcade)
            elif name in arcade.alias:
                arcade_list.append(arcade)
                
        return arcade_list
    
    def search_fullname(self, name: str) -> List[Arcade]:
        """查询店铺全名机厅"""
        arcade_list = []
        for arcade in self:
            if name == arcade.name:
                arcade_list.append(arcade)

        return arcade_list
    
    def search_alias(self, alias: str) -> List[Arcade]:
        """查询别名机厅"""
        arcade_list = []
        for arcade in self:
            if alias in arcade.alias:
                arcade_list.append(arcade)
        
        return arcade_list
    
    def search_id(self, id: str) -> List[Arcade]:
        """指定ID查询机厅"""
        arcade_list = []
        for arcade in self:
            if id == arcade.id:
                arcade_list.append(arcade)

        return arcade_list

    def add_arcade(self, arcade: dict) -> bool:
        """添加机厅"""
        self.append(Arcade(**arcade))
        return True

    def del_arcade(self, arcadeName: str) -> bool:
        """删除机厅"""
        for arcade in self:
            if arcadeName == arcade.name:
                self.remove(arcade)
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
        self.arcades: List[Dict] = json.load(open(arcades_json, 'r', encoding='utf-8'))
        self.idList = []

    def get_by_id(self, id: int) -> Union[None, Dict]:
        id_list = [c_a['id'] for c_a in self.arcades]
        if id in id_list:
            return self.arcades[id_list.index(id)]
        else:
            return None
    
    async def getArcade(self):
        self.total = await download_arcade_info()
        self.idList = [c_a.id for c_a in self.total]

arcade = ArcadeData()


async def download_arcade_info(save: bool = True) -> ArcadeList:
    try:
        async with aiohttp.request('GET', 'http://wc.wahlap.net/maidx/rest/location', timeout=aiohttp.ClientTimeout(total=30)) as req:
            if req.status == 200:
                data = await req.json()
            else:
                data = None
                loga.error('获取机厅信息失败')
        arcadelist = ArcadeList()
        if data is not None:
            if not arcade.arcades:
                for num in range(len(data)):
                    _arc = data[num]
                    arcade_dict = {
                        'name': _arc['arcadeName'],
                        'location': _arc['address'],
                        'province': _arc['province'],
                        'mall': _arc['mall'],
                        'num': _arc['machineCount'],
                        'id': _arc['id'],
                        'alias': [],
                        'group': [],
                        'person': 0,
                        'by': '',
                        'time': ''
                    }
                    arcadelist.append(Arcade(**arcade_dict))
            else:
                for num in range(len(data)):
                    _arc = data[num]
                    arcade_dict = arcade.get_by_id(_arc['id'])
                    if arcade_dict is not None:
                        arcade_dict['name'] = _arc['arcadeName']
                        arcade_dict['location'] = _arc['address']
                        arcade_dict['province'] = _arc['province']
                        arcade_dict['mall'] = _arc['mall']
                        arcade_dict['num'] = _arc['machineCount']
                        arcade_dict['id'] = _arc['id']
                    else:
                        arcade_dict = {
                            'name': _arc['arcadeName'],
                            'location': _arc['address'],
                            'province': _arc['province'],
                            'mall': _arc['mall'],
                            'num': _arc['machineCount'],
                            'id': _arc['id'],
                            'alias': [],
                            'group': [],
                            'person': 0,
                            'by': '',
                            'time': ''
                        }
                        arcade.arcades.insert(num, arcade_dict)
                    arcadelist.append(Arcade(**arcade_dict))
            for n in arcade.arcades:
                if int(n['id']) >= 10000:
                    arcadelist.append(Arcade(**n))
        else:
            for _a in arcade.arcades:
                arcadelist.append(Arcade(**_a))
        if save:
            await writefile(arcades_json, [_.model_dump() for _ in arcadelist])
        return arcadelist
    except Exception:
        loga.error(f'Error: {traceback.format_exc()}')
        loga.error('获取机厅信息失败')


async def updata_arcade(arcadeName: str, num: str):
    if arcadeName.isdigit():
        arcade_list = arcade.total.search_id(arcadeName)
    else:
        arcade_list = arcade.total.search_fullname(arcadeName)
    if arcade_list:
        _arcade = arcade_list[0]
        _arcade.num = int(num)
        msg = f'已修改机厅 [{arcadeName}] 机台数量为 [{num}]'
        await arcade.total.save_arcade()
    else:
        msg = f'未找到机厅：{arcadeName}'
    return msg
    

async def update_alias(arcadeName: str, aliasName: str, add_del: bool):
    """变更机厅别名"""
    change = False
    if arcadeName.isdigit():
        arcade_list = arcade.total.search_id(arcadeName)
    else:
        arcade_list = arcade.total.search_fullname(arcadeName)
    if arcade_list:
        _arcade = arcade_list[0]
        if add_del:
            if aliasName not in _arcade.alias:
                _arcade.alias.append(aliasName)
                msg = f'机厅：{_arcade.name}\n已添加别名：{aliasName}'
                change = True
            else:
                msg = f'机厅：{_arcade.name}\n已拥有别名：{aliasName}\n请勿重复添加'
        else:
            if aliasName in _arcade.alias:
                _arcade.alias.remove(aliasName)
                msg = f'机厅：{_arcade.name}\n已删除别名：{aliasName}'
                change = True
            else:
                msg = f'机厅：{_arcade.name}\n未拥有别名：{aliasName}'
    else:
        msg = f'未找到机厅：{arcadeName}'
    if change:
        await arcade.total.save_arcade()
    return msg


async def subscribe(group_id: int, arcadeName: str, sub: bool):
    """订阅机厅，`sub` 等于 `True` 为订阅，`False` 为取消订阅"""
    change = False
    if arcadeName.isdigit():
        arcade_list = arcade.total.search_id(arcadeName)
    else:
        arcade_list = arcade.total.search_fullname(arcadeName)
    if arcade_list:
        _arcade = arcade_list[0]
        if sub:
            if arcade.total.group_in_arcade(group_id, _arcade.name):
                msg = f'该群已订阅机厅：{_arcade.name}'
            else:
                _arcade.group.append(group_id)
                msg = f'群：{group_id} 已添加订阅机厅：{_arcade.name}'
                change = True
        else:
            if not arcade.total.group_in_arcade(group_id, _arcade.name):
                msg = f'该群未订阅机厅：{_arcade.name}，无需取消订阅'
            else:
                _arcade.group.remove(group_id)
                msg = f'群：{group_id} 已取消订阅机厅：{_arcade.name}'
                change = True
    else:
        msg = f'未找到机厅：{arcadeName}'
    if change:
        await arcade.total.save_arcade() 
    return msg
        
        
async def update_person(arcadeList: List[Arcade], userName: str, value: str, person: int):
    """变更机厅人数"""
    if len(arcadeList) == 1:
        _arcade = arcadeList[0]
        original_person = _arcade.person
        if value in ['+', '＋', '增加', '添加', '加']:
            if person > 30:
                return '请勿乱玩bot，恼！'
            _arcade.person += person
        elif value in ['-', '－', '减少', '降低', '减']:
            if person > 30 or person > _arcade.person:
                return '请勿乱玩bot，恼！'
            _arcade.person -= person
        elif value in ['=', '＝', '设置', '设定']:
            if abs(_arcade.person - person) > 30:
                return '请勿乱玩bot，恼！'
            _arcade.person = person
        if _arcade.person == original_person:
            return f'人数没有变化\n机厅：{_arcade.name}\n当前人数：{_arcade.person}'
        else:
            _arcade.by = userName
            _arcade.time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            await arcade.total.save_arcade()
            return f'机厅：{_arcade.name}\n当前人数：{_arcade.person}\n变更时间：{_arcade.time}'
    elif len(arcadeList) > 1:
        return '找到多个机厅，请使用id变更人数\n' + '\n'.join([f'{_.id}：{_.name}' for _ in arcadeList])
    else:
        return '没有找到指定机厅'
