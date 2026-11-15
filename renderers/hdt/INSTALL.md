# TavernLens · HDT 插件版

1. 结束当前对局后，退出 HDT。
2. 将整个 `TavernLens` 文件夹放进 HDT 的 `Plugins` 目录。
3. 启动 HDT，在“设置 → 插件”中启用 `TavernLens · 酒馆透镜`。
4. 等待下一次英雄或饰品选择。

不要只复制 DLL，保留同目录的 `TavernLensBackend.exe` 和 `_internal`。
数据服务由插件自动启动，无需安装 Python 或 Overwolf。禁用插件后，自动
启动的服务在闲置 60 秒后退出。

插件“设置”可调整分段、时间、模式、大小和两类卡牌的横纵位置。设置和缓存
保存在 `%LOCALAPPDATA%\TavernLens`。

已针对 HDT 1.59.8.0 编译，并通过独立测试宿主的渲染检查。尚未在你正在运行
的团子版 HDT 中实战验证，数据条位置可能需要微调。打包 EXE 的启动测试
曾被自动审批拦截，详情见 `VALIDATION.md`。

项目：[OpenBigc/TavernLens](https://github.com/OpenBigc/TavernLens)。
