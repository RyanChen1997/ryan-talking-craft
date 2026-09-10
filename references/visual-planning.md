# 画面方案

内容与素材先确认。选择顺序：信息关系 → 主要载体 → 候选模板 → 兼容布局 → 背景 → 配色 → 对齐口播。

模板、布局、背景与配色索引在 assets/visual-kit/catalog.json，代码入口和 README 一一对应。只选择当前索引中 `status` 为 `reviewed` 的模板和布局，以及已注册的背景／配色；旧组件与未晋级 staging 不在正式库中。按 `carrier` + `informationRelations` 缩小模板候选；布局在白板（`whiteboard-pip-*`）与录屏（`screen-full`、`screen-pip-*`）两组里选，再读对应 README。

每段 visual 包含 layout、template（可为 null，表示静态）、beats（简短的口播触发与展开顺序）、clips（媒体源范围）。不为稳定模板重复抄写内部所有动画帧。

全片 `output`、`background` 与 `palette` 写在 plan 顶层，不写在段落里。`output` 未经用户指定时保持初始化的 1920×1080，输入媒体比例不覆盖它。背景负责舞台，配色负责字／卡片／强调／字幕色。选定背景后读取 [color-planning.md](color-planning.md)，用口播联系表在兼容方案中选一套。模板只接收 `theme`，不拥有颜色。

预览工程是独立的仓库工具，不随 skill 安装。成片工程需要预览候选时，接入共享源码并只注册相关组件即可，不依赖仓库 preview 路径。配色对照入口：`Palette-Compare`。

录屏只允许时间裁剪；frame range 使用成片帧，source_in/source_out 使用源秒，禁止混淆。完成态要有阅读空间，但不套固定静止上限。
