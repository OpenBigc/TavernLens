# 开发与构建

需要 Windows、Python 3.10+、.NET Framework 4.x 编译器，以及已安装的 HDT。当前插件基于 HDT 1.59.8.0 构建。

## 构建安装包

```powershell
python -m pip install pyinstaller
powershell -NoProfile -File tools/package.ps1 -HdtPath "C:\路径\HDT"
```

输出：`dist/TavernLens-HDT.zip`。

## 开发与测试

```powershell
python run.py
python run.py --check-data
python run.py --replay "路径\Power.log"
python -m unittest discover -s tests -v
powershell -NoProfile -File tests/hdt/run.ps1
```

Python 核心负责日志识别、统计获取和缓存；插件实现 HDT 的 `IPlugin` 接口，将数据条挂到 `API.Core.OverlayCanvas`。界面与位置逻辑在 `renderers/hdt/Plugin.cs`。

设置和缓存位于 `%LOCALAPPDATA%\TavernLens`。本机数据桥接使用 `127.0.0.1:27183/state`；数据服务不创建独立评分窗口。

维护卡牌目录：`python tools/update_catalog.py`，然后重新构建。

- [HDT 插件接口](https://github.com/HearthSim/Hearthstone-Deck-Tracker/wiki/Creating-Plugins)
- [公开画布接口](https://github.com/HearthSim/Hearthstone-Deck-Tracker/blob/master/Hearthstone%20Deck%20Tracker/API/Core.cs)
