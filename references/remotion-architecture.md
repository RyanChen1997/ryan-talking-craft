# Remotion 工程职责

一个主 Composition 是正常的完整视频入口，不代表所有代码写在一个组件。普通场景用 React 组件与 Sequence；另注册独立 Composition 仅用于预览调试。

主入口负责连续 NarrationTrack、内容场景轨、独立静音真人视觉轨、全局 CaptionOverlay。布局必须用 `StageLayout` 按 catalog 变体分配区域（白板 ± PIP，或录屏 ± PIP），不要在成片侧复制布局比例或手工重建 PIP 外框。人物节点传给 `presenter`，圆角、溢出裁切和位置由布局拥有；白板关键内容按 `computeStageLayout(...).safe` 放置，背景可铺满 `content`。动效模板只接收内容、空间、时间和注入的 `theme`，不自己挂载口播音频，也不选择配色。`theme` 来自 `resolvePalette(plan.palette)`。

连续真人视觉轨保持源时间同步，布局只改变展示框或可见性。复杂删改、多机位、变速时建立共同编辑映射，每段明确成片帧范围与源秒数。Sequence 的局部帧不是全局帧；重新挂载的片段要设置正确源起点，不能从零播放。

所有动画由 useCurrentFrame、interpolate 等确定性帧计算驱动，无 CSS 动画或非种子随机。视频／音频 API 使用当前 Remotion 文档，不凭记忆猜 trim 参数。

安装共享库使用 install_motion_kit.py <project-root> --source <skill-dir>/assets/visual-kit；冲突默认报告、不覆盖用户修改。不要用脚本 force 绕过未知修改。

第一轮预览使用占位人物测试布局，不构成真实媒体同步验收。实际工程必须在跨镜头、隐藏后重新出现和结尾检查源时间映射。
