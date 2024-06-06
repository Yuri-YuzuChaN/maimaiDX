import json
from pathlib import Path
from typing import Dict, List

from hoshino import Service, priv
from hoshino.config import NICKNAME
from hoshino.log import new_logger

### 必须
log = new_logger('maimaiDX')
loga = new_logger('maimaiDXArcade')
BOTNAME = NICKNAME if isinstance(NICKNAME, str) else list(NICKNAME)[0]


SV_HELP = '请使用 帮助maimaiDX 查看帮助'
sv = Service('maimaiDX', manage_priv=priv.ADMIN, enable_on_default=True, help_=SV_HELP)

public_addr = 'https://www.yuzuchan.moe/vote'

# 文件路径
Root: Path = Path(__file__).parent
static: Path = Root / 'static'

arcades_json: Path = static / 'arcades.json'                    # 机厅
if not arcades_json.exists():
    arcades_json.write_text("[]")

config_json: Path = static / 'config.json'                      # token
alias_file: Path = static / 'music_alias.json'                  # 别名暂存文件
local_alias_file: Path = static / 'local_music_alias.json'      # 本地别名文件
music_file: Path = static / 'music_data.json'                   # 曲目暂存文件
chart_file: Path = static / 'music_chart.json'                  # 谱面数据暂存文件

guess_file: Path = static / 'group_guess_switch.json'           # 猜歌开关群文件
if not guess_file.exists():
    guess_file.write_text(json.dumps({"enable": [], "disable": []}, ensure_ascii=False, indent=4))

group_alias_file: Path = static / 'group_alias_switch.json'     # 别名推送开关群文件
if not group_alias_file.exists():
    group_alias_file.write_text(json.dumps({'enable': [], 'disable': [], 'global': True}, ensure_ascii=False, indent=4))

# 静态资源路径
maimaidir: Path = static / 'mai' / 'pic'
coverdir: Path = static / 'mai' / 'cover'
ratingdir: Path = static / 'mai' / 'rating'
platedir: Path = static / 'mai' / 'plate'

# 字体路径
MEIRYO: Path =  static / 'meiryo.ttc'
SIYUAN: Path = static / 'SourceHanSansSC-Bold.otf'
HANYI: Path = static / 'HanYi.ttf'
TBFONT: Path = static / 'Torus SemiBold.otf'


# 常用变量
SONGS_PER_PAGE: int = 25
scoreRank: List[str] = ['d', 'c', 'b', 'bb', 'bbb', 'a', 'aa', 'aaa', 's', 's+', 'ss', 'ss+', 'sss', 'sss+']
score_Rank: List[str] = ['d', 'c', 'b', 'bb', 'bbb', 'a', 'aa', 'aaa', 's', 'sp', 'ss', 'ssp', 'sss', 'sssp']
score_Rank_l: Dict[str, str] = {'d': 'D', 'c': 'C', 'b': 'B', 'bb': 'BB', 'bbb': 'BBB', 'a': 'A', 'aa': 'AA', 'aaa': 'AAA', 's': 'S', 'sp': 'Sp', 'ss': 'SS', 'ssp': 'SSp', 'sss': 'SSS', 'sssp': 'SSSp'}
comboRank: List[str] = ['fc', 'fc+', 'ap', 'ap+']
combo_rank: List[str] = ['fc', 'fcp', 'ap', 'app']
syncRank: List[str] = ['fs', 'fs+', 'fdx', 'fdx+', 'sp']
sync_rank: List[str] = ['fs', 'fsp', 'fsd', 'fsdp', 'sp']
sync_rank2: List[str] = ['fs', 'fsp', 'fdx', 'fdxp', 'sp']
diffs: List[str] = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:Master']
levelList: List[str] = ['1', '2', '3', '4', '5', '6', '7', '7+', '8', '8+', '9', '9+', '10', '10+', '11', '11+', '12', '12+', '13', '13+', '14', '14+', '15']
achievementList: List[float] = [50.0, 60.0, 70.0, 75.0, 80.0, 90.0, 94.0, 97.0, 98.0, 99.0, 99.5, 100.0, 100.5]
BaseRaSpp: List[float] = [7.0, 8.0, 9.6, 11.2, 12.0, 13.6, 15.2, 16.8, 20.0, 20.3, 20.8, 21.1, 21.6, 22.4]
fcl: Dict[str, str] = {'fc': 'FC', 'fcp': 'FCp', 'ap': 'AP', 'app': 'APp', 'sp': 'SP'}
fsl: Dict[str, str] = {'fs': 'FS', 'fsp': 'FSp', 'fsd': 'FSD', 'fdx': 'FSD', 'fsdp': 'FSDp', 'fdxp': 'FSDP', 'sync': 'SP', 'sp': 'SP'}
ignore_music: List[str] = ['70', '146', '189', '190', '341', '419', '451', '455', '460', '687', '688', '712', '731', '792', '853', '10146', '11213', '11253', '11267']
plate_to_version: Dict[str, str] = {
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
    '祝': 'maimai でらっくす FESTiVAL PLUS',
    '双': 'maimai でらっくす BUDDiES'
}
platecn = {
    '晓': '暁',
    '樱': '櫻',
    '堇': '菫',
    '辉': '輝',
    '华': '華'
}
category: Dict[str, str] = {
    '流行&动漫': 'anime',
    '舞萌': 'maimai',
    'niconico & VOCALOID': 'niconico',
    '东方Project': 'touhou',
    '其他游戏': 'game',
    '音击&中二节奏': 'ongeki',
    'POPSアニメ': 'anime',
    'maimai': 'maimai',
    'niconicoボーカロイド': 'niconico',
    '東方Project': 'touhou',
    'ゲームバラエティ': 'game',
    'オンゲキCHUNITHM': 'ongeki',
    '宴会場': '宴会场'
}