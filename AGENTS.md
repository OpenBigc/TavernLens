# TavernLens

- 只做酒馆战棋英雄和饰品统计；不要引入阵容、商店、战斗模拟、对局上传或内存读取。
- 所有产品界面使用简体中文，必要名称、数值、状态和动作之外不添加解释性文案。
- `engine.py` 不依赖 UI 或网络；`providers/` 不依赖 UI。Python 只提供数据服务，UI 挂到 HDT 的现有 OverlayCanvas。
- 正式渲染端只维护 `renderers/hdt`；不要引入 Overwolf、独立 Tk 窗口或游戏进程注入。
- ID、日志字段、接口字段使用原始值，中文仅用于显示。
- 数据来自真实接口；缺失分段、失败和过期缓存必须保持可区分，禁止伪造统计。
- 不提交用户设置、API 缓存、本机日志或构建产物。
- 修改识别逻辑后运行 `python -m unittest discover -s tests -v`。
- 修改 HDT 界面后运行 `powershell -NoProfile -File tests/hdt/run.ps1`。
