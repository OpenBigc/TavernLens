# HDT 渲染端

插件实现 HDT 的公开 `IPlugin` 接口，将一个不可点击的 Canvas 挂到
`Hearthstone_Deck_Tracker.API.Core.OverlayCanvas`，四条统计是 Canvas 的子控件。
不创建独立评分窗口，不注入炉石进程，显隐与前后台跟随 HDT。

统计和日志识别由独立无 UI 数据服务提供。插件读取本机
`http://127.0.0.1:27183/state`；网络失败或选择结束会清空自己添加的控件。
禁用插件会停止轮询并移除自己的 Canvas，不影响 HDT 原有内容。

## 构建与安装

```powershell
python -m PyInstaller TavernLens.spec --noconfirm
powershell -NoProfile -File renderers/hdt/build.ps1 -HdtPath "E:\Programs\HDT"
```

将完整 `dist/TavernLens` 文件夹放进 `%APPDATA%\HearthstoneDeckTracker\Plugins` 目录。不要只复制 DLL，
`TavernLensBackend.exe` 和 `_internal` 也需要一起保留。重启 HDT，然后在
设置 → 插件中启用 TavernLens。先结束当前对局，再重启 HDT。插件应安装到上述 AppData 目录；HDT 程序安装目录的 Plugins 会在同步时清理。

插件首次连不到服务时会尝试启动同目录的数据服务。禁用后，自动启动的服务
在 60 秒没有渲染端访问时退出。开发时也可运行 `python run.py` 手动提供服务。

“设置”提供分段、时间、单／双人、大小以及两类卡牌的横纵偏移。保存后无需
重启服务；修改筛选会重新获取统计。位置以居中 16:9 画布的百分比计算。

## 验证边界

已针对本机 HDT 1.59.8.0 编译。独立测试宿主验证画布挂载、四个槽位、点击
穿透、隐藏与卸载清理；本机团子版 HDT 已安装并启用，数据服务自动启动、日志读取和统计获取均已验证。
仍未完成选择画面的实战坐标验证。某些 HDT 分支可能修改
OverlayCanvas 的行为，需要在实际选择画面校准。

- [HDT 插件接口文档](https://github.com/HearthSim/Hearthstone-Deck-Tracker/wiki/Creating-Plugins)
- [公开画布接口](https://github.com/HearthSim/Hearthstone-Deck-Tracker/blob/master/Hearthstone%20Deck%20Tracker/API/Core.cs)
