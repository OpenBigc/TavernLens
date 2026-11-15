# TavernLens · 酒馆透镜

只做酒馆战棋英雄与饰品统计，通过 **HDT 插件**把数据挂到 HDT 现有悬浮画布。每张卡牌下方显示平均名次、选择率和样本数，保持游戏里的原始顺序。

没有阵容、商店、战斗模拟、其他玩家信息或对局上传。无需 Overwolf 账号，不修改炉石客户端。这里采用的是 HDT 式叠加显示，不是炉石原生 UI。

## 使用

将完整发布包里的 `TavernLens` 文件夹放进 HDT 的 Plugins 目录，重启 HDT，在插件设置中启用 TavernLens。先结束当前对局再重启。

包内包括一个小型 HDT 插件 DLL，以及无 UI 的统计数据服务。插件按需自动启动服务；禁用后服务闲置 60 秒自动退出。不需要安装 Python。不要只复制 DLL，需保留同目录的数据服务和 `_internal` 文件夹。

在 TavernLens 的插件“设置”里选择分段、时间、模式、大小和卡牌下方的位置偏移，保存后生效。原版 HDT／其他插件如已显示相同英雄饰品数据，可关闭其对应功能，避免重叠。

默认目录：`%LOCALAPPDATA%\TavernLens`，包含设置、缓存和诊断日志，不写入仓库。日志目录会自动查找注册表和常见安装位置，也可在 settings.json 中指定 `logs`。

需要炉石已启用 `[Power] FilePrinting=True`、`Verbose=True` 日志。中途启动会回填玩家身份，不展示历史选择；等待下一次英雄或饰品选择。战斗中提前写入日志的饰品选择会延迟到招募阶段显示。

## 当前验证情况

- 统计接口实测可访问，单人全分段当前补丁有 116 个英雄、239 个饰品。
- 检测核心通过上游 19 次英雄／36 次饰品选择回归，本机真实日志回放能识别两类选择。
- 插件已针对本机 HDT 1.59.8.0 编译。
- 独立 WPF 测试宿主验证了 HDT 画布挂载、四个选项顺序、不可点击、选择结束隐藏和卸载清理。
- **尚未在你当前运行的团子版 HDT 中启用插件并实战验证**；没有重启或改动正在运行的 HDT。下方初始坐标仍可能需要微调。

## 开发

数据核心使用 Python 3.10+ 标准库，无 Tk、Pillow 或其他运行时第三方依赖。插件使用 HDT 现有的 .NET Framework／WPF 环境。

```powershell
python run.py
python run.py --check-data
python run.py --replay "路径\Power.log"
python -m unittest discover -s tests -v
powershell -NoProfile -File tests/hdt/run.ps1
```

`run.py` 仅运行数据服务，不会弹出独立评分窗口。渲染桥接为只读本机接口 `127.0.0.1:27183/state`，不提供玩家昵称、原始日志、账号、远程命令或配置写入。

| 代码 | 职责 |
| --- | --- |
| `src/tavernlens/detection.py` | 从 bgtracker 抽出的选项检测 |
| `src/tavernlens/engine.py` | 英雄／饰品选择状态与显示时机 |
| `src/tavernlens/follower.py` | 日志回填与轮转 |
| `src/tavernlens/providers/firestone.py` | 数据源、分段和缓存 |
| `src/tavernlens/models.py` | 统计归一化与中文展示字段 |
| `src/tavernlens/service.py`、`bridge.py` | 无 UI 本机数据服务 |
| `renderers/hdt/Plugin.cs` | HDT 画布、卡牌位置、样式和中文设置 |

后续改 UI，主要改 `renderers/hdt/Plugin.cs`；统计和日志逻辑无需重写。未采用的桌面／Overwolf 试验放在本机 gitignored 的 work 下，不进入主仓库。

构建：

```powershell
python -m pip install pyinstaller
python -m PyInstaller TavernLens.spec --noconfirm
powershell -NoProfile -File renderers/hdt/build.ps1 -HdtPath "E:\Programs\HDT"
```

输出 `dist/TavernLens/`。HDT 主程序仅作为编译引用，不会随包分发。维护新版本卡牌目录：`python tools/update_catalog.py` 后重建。

一次性构建并生成安装包：`powershell -NoProfile -File tools/package.ps1 -HdtPath "E:\Programs\HDT"`。
输出 `dist/TavernLens-HDT.zip`，包内有安装说明。

## 数据口径

统计读取 Firestone 客户端使用的公开可访问地址：

```text
主机：https://static.zerotoheroes.com
英雄：/api/bgs/hero-stats/mmr-{mmr}/{period}/overview-from-hourly.gz.json
饰品：/api/bgs/trinket-stats/{period}/overview-from-hourly.gz.json
双人英雄：/api/bgs/duo/hero-stats/mmr-{mmr}/{period}/overview-from-hourly.gz.json
```

分段：全体、前 50%、25%、10%、1%；时间：当前补丁、近 7 天、近 3 天、全部时间。只逐一实测了单人全分段当前补丁，其他组合取决于服务端是否提供。双人饰品尚无数据源，不用单人数据替代。

饰品平均名次与样本数取自同一分段；只有总体选择率时标为“总体选择”。缺少所选分段时显示暂无数据，少于 30 场标记样本少。平均名次越低越好，不代表因果收益或针对当前阵容的预测。

缓存一小时，接口失败时可回退旧缓存并标记。公开可访问不等于正式的开放 API 或数据再发布许可，接口可能调整或关闭。仓库不含 Firestone 统计副本。

内置英雄／饰品中文名称与 ID 来自 HearthstoneJSON，目录约 32 KB，不附带原画。代码许可证不覆盖暴雪名称或第三方统计。

## 来源

- [bgtracker](https://github.com/BattlegroundsHelp/bgtracker)，抽取部分保留 MIT 版权说明。
- [HDT 插件开发接口](https://github.com/HearthSim/Hearthstone-Deck-Tracker/wiki/Creating-Plugins)。
- [Firestone 英雄接口源码](https://github.com/Zero-to-Heroes/firestone/blob/master/libs/battlegrounds/data-access/src/lib/meta-heroes/bgs-meta-hero-stats-access.service.ts)。
- [Firestone 饰品接口源码](https://github.com/Zero-to-Heroes/firestone/blob/master/libs/battlegrounds/services/src/lib/services/bgs-trinkets.service.ts)。

详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
