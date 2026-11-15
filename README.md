# TavernLens · 酒馆透镜

HDT 的酒馆战棋插件，在每张英雄和饰品卡牌下方显示平均名次、选择率和样本数。

## 使用

需要 Windows 和 [Hearthstone Deck Tracker](https://github.com/HearthSim/Hearthstone-Deck-Tracker)。

1. 从 [Releases](https://github.com/OpenBigc/TavernLens/releases/latest) 下载 `TavernLens-HDT.zip`。
2. 退出 HDT，将解压后的整个 `TavernLens` 文件夹放入：
   ```text
   %APPDATA%\HearthstoneDeckTracker\Plugins
   ```
3. 启动 HDT，在“设置 → 插件”中启用 **TavernLens · 酒馆透镜**。
4. 进入酒馆战棋，在选择英雄或饰品时查看数据。

保留文件夹内的全部文件，无需安装 Python。插件设置可调整分段、时间范围、数据条大小和位置。平均名次越低越好；双人模式暂只提供英雄统计。

统计来自 Firestone，中文卡名来自 HearthstoneJSON。

[源码构建](renderers/hdt/README.md) · [MIT](LICENSE) · [第三方声明](THIRD_PARTY_NOTICES.md)
