import json
import os
from typing import Dict, List

from hoshino.config import NICKNAME
from hoshino.log import new_logger

### 必须
log = new_logger('maimaiDX')
loga = new_logger('maimaiDXArcade')
BOTNAME = NICKNAME if isinstance(NICKNAME, str) else list(NICKNAME)[0]


### 文件路径
Root = os.path.dirname(__file__)
static = os.path.join(Root, 'static')
arcades_json = os.path.join(static, 'arcades.json')             # 机厅
config_json = os.path.join(static, 'config.json')               # token
alias_file = os.path.join(static, 'all_alias.json')             # 别名暂存文件
music_file = os.path.join(static, 'music_data.json')            # 曲目暂存文件
chart_file = os.path.join(static, 'chart_stats.json')           # 谱面数据暂存文件
guess_file = os.path.join(static, 'guess_config.json')          # 猜歌开关群文件
group_alias_file = os.path.join(static, 'group_alias.json')     # 别名推送开关群文件
maimaidir = os.path.join(static, 'mai', 'pic')
coverdir = os.path.join(static, 'mai', 'cover')
ratingdir = os.path.join(static, 'mai', 'rating')
MEIRYO =  os.path.join(static, 'meiryo.ttc')
SIYUAN = os.path.join(static, 'SourceHanSansSC-Bold.otf')
TBFONT = os.path.join(static, 'Torus SemiBold.otf')


### 加载文件
if not os.path.exists(arcades_json):
    raise FileNotFoundError
arcades: List[Dict] = json.load(open(arcades_json, 'r', encoding='utf-8'))
token = json.load(open(config_json, 'r', encoding='utf-8'))['token']


### 常用变量
SONGS_PER_PAGE = 25
scoreRank = ['d', 'c', 'b', 'bb', 'bbb', 'a', 'aa', 'aaa', 's', 's+', 'ss', 'ss+', 'sss', 'sss+']
score_Rank = {'d': 'D', 'c': 'C', 'b': 'B', 'bb': 'BB', 'bbb': 'BBB', 'a': 'A', 'aa': 'AA', 'aaa': 'AAA', 's': 'S', 'sp': 'Sp', 'ss': 'SS', 'ssp': 'SSp', 'sss': 'SSS', 'sssp': 'SSSp'}
comboRank = ['fc', 'fc+', 'ap', 'ap+']
combo_rank = ['fc', 'fcp', 'ap', 'app']
syncRank = ['fs', 'fs+', 'fdx', 'fdx+']
sync_rank = ['fs', 'fsp', 'fsd', 'fsdp']
diffs = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:Master']
levelList = ['1', '2', '3', '4', '5', '6', '7', '7+', '8', '8+', '9', '9+', '10', '10+', '11', '11+', '12', '12+', '13', '13+', '14', '14+', '15']
achievementList = [50.0, 60.0, 70.0, 75.0, 80.0, 90.0, 94.0, 97.0, 98.0, 99.0, 99.5, 100.0, 100.5]
BaseRaSpp = [7.0, 8.0, 9.6, 11.2, 12.0, 13.6, 15.2, 16.8, 20.0, 20.3, 20.8, 21.1, 21.6, 22.4]
fcl = {'fc': 'FC', 'fcp': 'FCp', 'ap': 'AP', 'app': 'APp'}
fsl = {'fs': 'FS', 'fsp': 'FSp', 'fsd': 'FSD', 'fsdp': 'FSDp'}
plate_to_version = {
    '初': 'maimai',
    '真': 'maimai PLUS',
    '超': 'maimai GreeN',
    '檄': 'maimai GreeN PLUS',
    '橙': 'maimai ORANGE',
    '暁': 'maimai ORANGE PLUS',
    '晓': 'maimai ORANGE PLUS',
    '桃': 'maimai PiNK',
    '櫻': 'maimai PiNK PLUS',
    '樱': 'maimai PiNK PLUS',
    '紫': 'maimai MURASAKi',
    '菫': 'maimai MURASAKi PLUS',
    '堇': 'maimai MURASAKi PLUS',
    '白': 'maimai MiLK',
    '雪': 'MiLK PLUS',
    '輝': 'maimai FiNALE',
    '辉': 'maimai FiNALE',
    '熊': 'maimai でらっくす',
    '華': 'maimai でらっくす PLUS',
    '华': 'maimai でらっくす PLUS',
    '爽': 'maimai でらっくす Splash',
    '煌': 'maimai でらっくす Splash PLUS',
    '宙': 'maimai でらっくす UNiVERSE',
    '星': 'maimai でらっくす UNiVERSE PLUS',
    '祭': 'maimai でらっくす FESTiVAL',
    '祝': 'maimai でらっくす FESTiVAL PLUS'
}
category = {
    '流行&动漫': 'anime',
    '舞萌': 'maimai',
    'niconico & VOCALOID': 'niconico',
    '东方Project': 'touhou',
    '其他游戏': 'game',
    '音击&中二节奏': 'ongeki'
}