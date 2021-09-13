# maimaiDX

移植自 xybot 及 [mai-bot](https://github.com/Diving-Fish/mai-bot) 开源项目，基于HoshinoBot v2的街机音游 **舞萌DX** 的查询插件

项目地址：https://github.com/Yuri-YuzuChaN/maimaiDX

## 使用方法

1. 将该项目放在HoshinoBot插件目录 `modules` 下，或者clone本项目 `git clone https://github.com/Yuri-YuzuChaN/maimaiDX`
2. 下载静态资源文件，将该压缩文件解压至插件根目录，即 `maimaiDX/static` ，[下载链接](https://www.diving-fish.com/maibot/static.zip)
4. pip以下依赖：`pillow`
5. 在`config/__bot__.py`模块列表中添加 `maimaiDX`
6. 重启HoshinoBot

## 指令

| 命令                                           | 功能                   |
| ---------------------------------------------- | ---------------------- |
| 帮助 maimaiDX                                  | 查看帮助文档           |
| 今日舞萌                                       | 查看今天的舞萌运势     |
| XXXmaimaiXXX什么                               | 随机一首歌             |
| 随个[dx/标准][绿黄红紫白]<难度>                | 随机一首指定条件的乐曲 |
| 查歌<乐曲标题的一部分>                         | 查询符合条件的乐曲     |
| [绿黄红紫白]id<歌曲编号>                       | 查询乐曲信息或谱面信息 |
| <歌曲别名>是什么歌                             | 查询乐曲别名对应的乐曲 |
| 定数查歌 <定数> 定数查歌 <定数下限> <定数上限>  | 查询定数对应的乐曲     |
| 分数线 <难度+歌曲id> <分数线>                  | 展示歌曲的分数线       |
| 开启/关闭mai猜歌                               | 开关猜歌功能            |
| 猜歌                                           |顾名思义，识别id，歌名和别称|
| b40 <游戏名>                                   | 查询b40                |

## 更新说明

# 2021-09-13 

1.更新猜歌功能以及开关，感谢 [BlueDeer233](https://github.com/BlueDeer233) 


## 鸣谢

感谢 [Diving-Fish](https://github.com/Diving-Fish) 提供的源码支持
感谢 [BlueDeer233](https://github.com/BlueDeer233) 提供猜歌功能的源码支持

## License

MIT

您可以自由使用本项目的代码用于商业或非商业的用途，但必须附带 MIT 授权协议。
