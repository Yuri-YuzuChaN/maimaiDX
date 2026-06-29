<div align='center'>

<a><img src='https://raw.githubusercontent.com/Yuri-YuzuChaN/nonebot-plugin-maimaidx/master/favicon.png' width='200px' height='200px' akt='maimaidx'></a>

<h1>maimaiDX</h1>

[![python3](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
</div>


移植自[mai-bot](https://github.com/Diving-Fish/mai-bot) 开源项目，基于 [HoshinoBotV2](https://github.com/Ice-Cirno/HoshinoBot) 的街机音游 **舞萌DX** 的查询插件

项目地址：https://github.com/Yuri-YuzuChaN/maimaiDX

#### 欢迎加入开发群交流：[QQGroup](https://qm.qq.com/q/gDIf3fGSPe)

## 重要更新

**2026-06-30**

1. 替换 `rating` 数字新素材，直接覆盖 `mai/pic` 目录，增量包：

   - [Cloudreve私人云盘](https://cloud.yuzuchan.moe/f/Jvhl/Resource%20CN1.56%20UPDATE.7z)
   - [onedrive](https://yuzuai-my.sharepoint.com/:u:/g/personal/yuzu_yuzuchan_moe/IQDS_RzM66klSqvHtUhfFPTfAfpJcbGlIbL-7Q6eSPxM4CA?e=xRPo7b)
   - [openlist](https://share.yuzuchan.moe/d/downloads/Resource%20CN1.56%20UPDATE.7z?sign=p6h2Q9f3u87vRO8yU6ZSvCoagq0BE-xnX4wlhM55s_U=:0)

2. 恢复查询TA人成绩的功能
3. 修复15完成表绘图偏移的问题
4. 修复进度表完成时文字重叠的问题
5. 优化部分绘图
6. 修复部分bug

**2026-06-09**

### 现仅支持 `Python 3.10+` ！！！

#### 最好在更新 `舞萌DX 2026` 后再使用该版本

1. 更新支持 `舞萌DX2026`，应该是最后一次大改了
2. 新支持了 `落雪查分器`
3. 新功能：
   - 新增 `舞`，`霸者` 牌子绘图
   - 新增进度绘图
   - 新增查询曲目过多时的绘图
   - 新增切换主题功能
   - 新增切换查分器功能
   - 新增 `ap50` 指令（仅限落雪查分器）
   - 新增 `lxbind`，`授权码`，`主题`，`数据源` 指令
   - 新增 `牌子条件` 指令
4. 新版本使用独立的 `log`
5. 新版本使用 `.env` 文件进行配置
6. 修改了别名推送的发送方式，防止刷屏
7. 修复了非常多的 `BUG`


## 温馨提示

**请务必看完 `README.MD` 所有内容**

## 使用方法

1. 将该项目放在HoshinoBot插件目录 `modules` 下，或者clone本项目
   
    ``` git
    git clone https://github.com/Yuri-YuzuChaN/maimaiDX
    ```
   
2. 下载静态资源文件，将该压缩文件解压后，将 `static` 文件夹复制到随意一个文件夹进行存放。对于先前使用过的开发者，请将原先 `static` 文件夹内的所有 `json` 文件放置到 `static/data` 文件夹，字体文件放置到 `static/font` 文件夹

   ## 对于美术的声明，请勿将绘图设计署名进行删除

   - [Cloudreve私人云盘](https://cloud.yuzuchan.moe/f/34s7/Resource%20CN1.55.7z)
   - [onedrive](https://yuzuai-my.sharepoint.com/:u:/g/personal/yuzu_yuzuchan_moe/IQBGKHie6MAaTZy3rME7Q-ruAVKgXDCKROqz5e25KtMeeVY?e=53eC6a)
   - [openlist](https://share.yuzuchan.moe/d/downloads/Resource%20CN1.55.7z?sign=4wMRn_9n6YZiEVV2vELKCEOj9zsgxScnmgtjsEL3C6g=:0)

3. 配置可选项，请复制 `.env.example` 文件并修改为 `.env`，根据要求填写

   ```
   # maimaidx                           # 基本配置
   MAIMAIDX_PATH=                       # 必填项，静态文件夹路径，必须为绝对路径到 `/static`，例如：e:/SakuraBOT/nbstatic/maimaidx/static
   MAIMAIDX_ALIAS_PUSH=true             # 是否开启别名推送
   MAIMAIDX_ALIAS_PROXY=false           # 是否使用中转访问柚子别名服务器，适用于境内服务器
   SAVE_IN_MEMORY=true                  # 是否将部分图片保存在内存
   ASSETS_ONLINE=true                   # 对于有 `icon` 和 `plate` 资源的可将此项改为 `false`，如果没有请默认，否则使用落雪查分器时无法使用

   # diving-fish                        # 水鱼查分器配置
   DIVINGFISH_TOKEN=                    # 开发者 token，由于水鱼查分器修改了请求鉴权，未填写的仅可使用 `b50` 指令
   DIVINGFISH_PROBER_PROXY=false        # 是否使用中转访问水鱼查分器，适用于境外服务器

   # lxns                               # 落雪查分器配置，均未填写将无法使用落雪查分器
   LXNS_DEV_TOKEN=                      # 开发者 token
   LX_CLIENT_ID=                        # OAuth 应用ID，OAuth权限范围请选择前三项，不包括「读取个人API秘钥」
   LX_CLIENT_SECRET=                    # OAuth 应用秘钥
   REDIRECT_URI=                        # OAuth 回调地址
   ```

4. 安装插件所需模块：`pip install -r requirements.txt`
5. 安装 `chromium`，**相关依赖已安装，请直接使用该指令执行**
   
   ``` shell
   playwright install --with-deps chromium
   ```

6. 安装 `微软雅黑` 字体，解决使用 `ginfo` 指令字体不渲染的问题，例如 `ubuntu`：`apt install fonts-wqy-microhei`，`windows` 平台可跳过
7. 在 `config/__bot__.py` 模块列表中添加 `maimaiDX`
8. 重启 `HoshinoBot`
9.  使用 `更新定数表`，`更新完成表` 指令完成图片生成
10. 开始使用

## 更新说明

<details>
<summary>Version 3.0 更新日志</summary>

**2026-06-09**

1. 更新支持 `舞萌DX2026`，应该是最后一次大改了
2. 新支持了 `落雪查分器`
3. 新功能：
   - 新增 `舞`，`霸者` 牌子绘图
   - 新增进度绘图
   - 新增查询曲目过多时的绘图
   - 新增切换主题功能
   - 新增切换查分器功能
   - 新增 `ap50` 指令（仅限落雪查分器）
   - 新增 `lxbind`，`授权码`，`主题`，`数据源` 指令
   - 新增 `牌子条件` 指令
4. 新版本使用独立的 `log`
5. 新版本使用 `.env` 文件进行配置
6. 修改了别名推送的发送方式，防止刷屏
7. 修复了非常多的 `BUG`
</details>

<details>
<summary>Version 2.0 更新日志</summary>

**2025-08-16**

1. 修改别名推送机制，请各开发者进行取舍
   
   - 更新别名推送设置与指令，新增了 `maimaidxaliaspush` 配置项，该设置将替代原先 `group_alias_switch.json` 文件的 `global_switch` 配置项
   - 当设置为`false` 时，不再连接别名推送服务器，如果群组的推送为开启状态，也不再进行推送，**与原先一致**。**申请的别名通过审核了也不再推送**

    ``` ujson
    {
        "enable": [],
        "disable": [88888888],
        "global_switch": false      // 该配置项将被代替并删除
    }
    ```

   - 不会接收到别名申请以及别名通过的消息，**如果服务器新增新的别名时无法实时获取最新的别名，仅能手动更新别名库**。

2. 指令 `全局开启/关闭别名推送` 的功能将修改为开关全部群组的推送开关。
3. 新增别名推送服务器代理地址，修改 `maimaiDX/static/config.json` 文件的 `maimaidxaliaspush` 配置项即可，~~其实是忘记添加代理地址~~

**2025-06-11**

1. 1. 更新 `舞萌DX2025` ，资源全部更换，更新部分依赖和文件

**2025-03-28**

1. 预更新 `舞萌DX2025` UI
2. 修改所有 `BOT管理员` 私聊指令为群聊指令：`更新别名库`、`更新maimai数据`、`更新定数表`、`更新完成表`

</details>

<details>
<summary>Version 1.0 更新日志</summary>

**2024-07-24**

1. 更新部分牌子完成表和 `SyncPlay` 图片
2. 修复 `新增机厅` 指令 `id` 未增加的问题
3. 修复 `牌子进度` 指令 `sync` 未匹配的问题
4. 修复 `别名查歌` 指令查询到已删除的曲目时发生错误的问题

**2024-06-07**

1. 更新至 `舞萌DX 2024`
2. 更换所有图片绘制，需删除除 `json` 后缀的所有文件，**请重新进行使用方法第二步**
3. 更改部分 `json` 文件名称，便于识别，具体文件如下，**请务必修改文件名，否则开关文件以及本地别名文件将不会被读取**
   - `all_alias.json`    修改为 `music_alias.json`
   - `local_alias.json`  修改为 `local_music_alias.json`
   - `chart_stats.json`  修改为 `music_chart.json`
   - `group_alias.json`  修改为 `group_alias_switch.json`
   - `guess_config.json` 修改为 `group_guess_switch.json`
4. 新增管理员私聊指令 `更新完成表`，用于更新 `BUDDiES` 版本 `双系` 牌子
5. 新增指令 `完成表`，可查询牌子完成表，例如：`祝极完成表`
6. 新增指令 `猜曲绘`
7. 查看谱面支持计算个人加分情况，指令包括 `是什么歌`，`id`
8. 指令 `mai什么` 支持随机发送推分谱面，指令中需包含 `加分`，`上分` 字样，例如：`今日mai打什么上分`
9.  修改指令 `分数列表` 和 `进度` 发送方式
10. 优化所有模块

**2024-03-12**

1. 变更别名服务器地址
2. 修改所有别名请求以及参数
3. 开放普通用户申请别名

**2024-01-14**

1. 优先使用本地谱面
2. 使用 `numpy` 模块重新绘制定数表

**2023-09-23**

1. 重写 `API` 方法
2. 重写机厅模块
3. 将同步生成定数表方法修改为异步方法，防止堵塞进程
4. 将 `当前别名投票` 发送方式修改为图片形式
5. 本地添加别名单独存储为一个文件，不再添加在暂存别名文件中

**2023-08-10**

1. 新增后缀指令 `定数表`，`完成表`，查询指定等级的定数表和完成表，例如：`13+完成表`
2. 新增BOT管理员私聊指令 `更新定数表`，用于生成和更新定数表
3. 新增BOT管理员私聊指令 `更新maimai数据`，用于版本更新手动更新bot已存数据
4. 拆分并移除 `maimaidx_project.py` 的代码和文件，便于所有功能维护
5. 修复曲绘不存在时下载错误的问题
6. 修复猜歌提前发出答案的bug
7. 修改指令 `minfo` 部分绘图

**2023-06-15**

1. 新增添加本地别名的功能

**2023-06-09**

1. 更新至 `舞萌DX 2023`
2. 移除指令 `b40`
3. 更换静态资源
4. 修改指令 `b50` 部分绘图

**2023-04-22**

1. 限制所有网络请求时长
2. 新增别名文件本地备份
3. 新增ginfo指令默认使用紫谱数据

**2023-04-21**

1. 新增BOT管理员私聊指令 `全局关闭别名推送` 和 `全局开启别名推送`，关闭所有群的推送消息，无论先前开启还是关闭
2. 修复新版本更新后API暂未收录曲目的问题
3. 新增乐曲游玩总览 `ginfo` 指令
4. 新增猜歌库根据乐曲游玩次数添加
5. 新增每日更新机厅信息，删除旧版更新机厅机制

**2023-04-15**

1. 将获取数据的方式由启动Bot时获取改为连接到CQHTTP后获取
2. 修复因查分器API内容变动而无法启动Bot的问题

**2023-03-29**

1. 重制 `b40/b50` ，`minfo` 和曲目信息的绘图
2. 修改投票网页端，改成共用网站
3. 修改垃圾代码

**2023-03-02**

1. 新增 `开启别名推送` 和 `关闭别名推送` 指令

**2023-02-25**

1. 修复猜歌答对后无法结束的问题

**2023-02-23**

1. 投票网页端

**2023-02-22**

1. 修复启动BOT时无法获取所有曲目信息的问题，添加本地缓存
2. 修改别名库，使用API获取和添加，并同步所有使用该插件的BOT
3. 修改猜歌和别名功能
4. 新增指令 `当前别名投票` 和 `同意别名`

**2023-2-18**

1. 别称同步临时解决方案 #47

**2023-2-15**

1. 更新本地缓存水鱼网数据 #43

**2022-9-14**

1. 新增查询单曲指令 `minfo`
2. 修改查曲绘图

**2022-8-30**

1. 修复新版b40/b50 isinstance bug [#38](https://github.com/Yuri-YuzuChaN/maimaiDX/issues/38)
2. 修复新版b40/b50 找不到图片问题
3. 修复安慰分隐性bug

**2022-08-27**

1. 修复b40/b50小数点后四位错误的问题

**2022-08-25**

1. 修复猜歌模块发送曲绘时为未知曲绘的问题

**2022-08-16**

1. 修改 `b40/b50` 指令绘图，如不喜欢请将 `libraries/maimaidx_project.py` 第`6`行 `maimai_best_50` 改成 `maimai_best_40`
2. 修改查曲绘图

**2022-07-11**

1. 修复指令 `分数列表` 没有提供2022谱面的问题

**2022-06-23**

1. 支持2022
2. 修改所有曲绘后缀
3. 修改获取在线文件的路径

**2022-03-10**

1. 新增段位显示，感谢 [Kurokitu](https://github.com/Kurokitu) 提供源码及资源

**2022-02-13**

1. 修复部分新曲没有难易度参考的问题

**2022-01-27**

1. 修复添加/删除别名无效的问题

**2022-01-16**

1. 修复b40/b50查询@Ta人情况下无效的问题

**2022-01-03**

1. 修改获取音乐数据的函数，不在使用同步进程
2. 不再使用正则表达式获取@人员的QQ号
3. 不再使用CQ码方式发送图片
4. 修改大部分源码

**2021-11-15**

1. 在请求获取maimaiDX数据的函数添加 `@retry` 装饰器，遇到请求数据失败的情况时重新尝试请求

**2021-10-18**

1. 添加排卡功能，感谢 [CrazyKid](https://github.com/CrazyKidCN)

**2021-10-14**

1. 更新查看推荐的上分乐曲
2. 更新查看牌子完成进度
3. 更新查看等级评价完成进度
4. 查看水鱼网站的用户ra排行

**2021-09-29**

1. 更新b50、乐曲推荐功能，感谢 [BlueDeer233](https://github.com/BlueDeer233) 

**2021-09-13** 

1. 更新猜歌功能以及开关，感谢 [BlueDeer233](https://github.com/BlueDeer233) 
   
</details>

## 鸣谢

感谢 [蓝色彗星](#) 提供的 `牌子条件` 指令图片

感谢 [zhanbao2000](https://github.com/zhanbao2000) 提供的 `nonebot2` 分支

感谢 [CrazyKid](https://github.com/CrazyKidCN) 提供的源码支持

感谢 [Diving-Fish](https://github.com/Diving-Fish) 提供的源码支持

感谢 [BlueDeer233](https://github.com/BlueDeer233) 提供猜歌功能的源码支持

## License

MIT

您可以自由使用本项目的代码用于商业或非商业的用途，但必须附带 MIT 授权协议。
