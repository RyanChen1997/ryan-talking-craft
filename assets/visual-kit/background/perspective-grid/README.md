# 黑底动态透视网格

ID：perspective-grid@1。用户明确要求恢复的背景，来源为历史 PerspectiveGridBackground 实现。代码自包含，不导入归档。

效果：黑色底、低对比暖白色透视线，横线缓慢向观众移动。以 Remotion 帧驱动，无 CSS 动画或随机值。

参数：canvas（默认 #08080A）、lineRgb（默认 232,228,218；纯白可用 255,255,255）、linesPerSecond（默认 0.8；0 为静态）、verticalGap（默认 258，最小 8）。本次保持原有运动和配色，不重设计。上屏文字、卡片和强调色不由本组件提供，需搭配 catalog 中兼容的 dark palette。

放在 Composition 最底层、人物和内容后面。背景不能覆盖录屏，也不要求内容或模板自带底色。该背景是用户选定的环境纹理，不作为额外语义动效计数。

预览：Background-Grid；Background-Captions 展示真实 CaptionOverlay，可调字幕底色不透明度。其他模板／布局预览可在 background 参数中选择 grid。
