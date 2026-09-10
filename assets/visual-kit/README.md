# 当前共享视觉库

只包含当前接入的模板、布局和必要运行时，不包含历史 Gallery、旧注册表或未迁移组件。

- templates/：已审阅晋级的 React/Remotion 模板，每个有 Template.tsx 和 README.md。按载体与信息关系分子目录：`typography/emphasis`、`typography/kinetic-type`、`diagram/data-chart`。
- layouts/：已审阅舞台布局，共享 `layouts/stage/Layout.tsx`。变体：白板左／右 PIP、录屏全屏、录屏 + 左／右 PIP。
- background/：用户明确恢复的黑底动态透视网格，自包含，不引用归档。
- palettes/：注册配色方案。模板只消费颜色角色，全片由成片入口注入 theme。
- runtime/：字幕、主音轨、完整录屏组件，不是动效模板。
- catalog.json：当前模板／布局／背景／配色唯一索引。只选择索引中的条目。
- motion.ts、tokens.ts、types.ts：公共运动工具、颜色角色与类型。
- index.ts：当前库公开导出。

代码由独立 preview 与安装后的成片工程共用，不引用 archive 或 preview。运行时依赖由成片工程提供：React 19、Remotion 4、@remotion/media；预览锁定 4.0.522。

旧 ordered-steps / before-after 适配模板和旧 presenter 分区布局已移除，不再进入正式库或预览。其他旧内容仅保留在仓库 archive/legacy，不安装、不预览。
