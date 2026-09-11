# 当前共享视觉库

只包含当前接入的模板、布局和必要运行时，不包含历史 Gallery、旧注册表或未迁移组件。

- templates/：已审阅晋级的 React/Remotion 模板，每个有 Template.tsx 和 README.md。按载体与信息关系分子目录：`typography/emphasis`、`typography/kinetic-type`、`typography/before-after`、`media-display/before-after`、`diagram/data-chart`。
- layouts/：已审阅舞台布局，共享 `layouts/stage/Layout.tsx`。变体：白板左／右 PIP、录屏全屏、录屏 + 左／右 PIP。
- background/：用户明确恢复的黑底动态透视网格，自包含，不引用归档。
- palettes/：注册配色方案。模板只消费颜色角色，全片由成片入口注入 theme。
- runtime/：字幕、主音轨、完整录屏组件，不是动效模板。
- catalog.json：当前模板／布局／背景／配色唯一索引。只选择索引中的条目。
- motion.ts、tokens.ts、types.ts：公共运动工具、颜色角色与类型。
- index.ts：当前库公开导出。

## 模板的两层

每个模板包含两层，处理方式相反：

- **动效本体**：时序表、缓动与逐帧计算、错峰与收尾节奏、DOM 结构。已验证资产，使用时原样保留。
- **演示语境**：为了能独立预览而写死的演示文案、根节点白色纸面背景、单个写死的强调色。属于占位，接入时必须替换。

所以 templates/ 里的 Template.tsx 不是可直接上屏的成品画面，而是**动效参考**；README 只写适用场景与动效描述，不写接入示例。成片侧从模板**摘取动效本体**到项目自己的场景组件，参考模板保持只读；规程见 skill 的 `references/visual-principles.md`「使用模板」。

代码由独立 preview 与安装后的成片工程共用，不引用 archive 或 preview。运行时依赖由成片工程提供：React 19、Remotion 4、@remotion/media；预览锁定 4.0.522。

旧 ordered-steps 适配模板、旧 before-after 适配模板（`state-transition`）和旧 presenter 分区布局已移除，不再进入正式库或预览。现有 `before-after` 目录是 2026 年根据真实参考片重新实现并通过审阅的新条目，不是旧适配模板的回流。其他旧内容仅保留在仓库 archive/legacy，不安装、不预览。
