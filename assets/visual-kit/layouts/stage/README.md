# StageLayout

共享实现：`Layout.tsx`、`geometry.ts`。按 catalog id 选择变体，不要再用旧的 `presenter-layout@1`。

| ID | 变体 | 适用场景 |
| --- | --- | --- |
| `whiteboard-pip-right@1` | 整幅白板，PIP 靠右 | 文字、图片、动效为主；人物画中画垂直居中浮在右侧 |
| `whiteboard-pip-left@1` | 整幅白板，PIP 靠左 | 同上，人物在左侧 |
| `screen-full@1` | 录屏铺满，隐藏 PIP | 录屏画幅可以完整 contain 进内容区时，只展示录屏 |
| `screen-pip-right@1` | 录屏 + 右侧 PIP | 录屏完整 contain；PIP 压在录屏靠近右侧的边上 |
| `screen-pip-left@1` | 录屏 + 左侧 PIP | 同上，人物在左侧 |

布局只分配区域，不管理视频源时间、音频或内部动画。录屏必须 `object-fit: contain`，禁止 cover、裁边、推近。白板变体的 `safe` 矩形是避开 PIP 的内容安全区，标题、卡片、图片、动效和其他关键文案都以这里为坐标系；整幅 `content` 只用于背景和非关键信息。

调用方必须直接渲染 `StageLayout`：人物传入 `presenter`，不要根据 `computeStageLayout()` 返回值手工创建另一个 PIP div。正式圆角与溢出裁切由 presenter 槽统一拥有；人物内容填满槽，并按人脸／手势安全要求选择适配。`computeStageLayout()` 可用于定位 safe 内容，但不能用于绕开布局容器。

切换默认硬切。`screen-full` 不渲染 PIP。人物媒体由调用方提供并静音；布局不裁切录屏。人物独立裁切只作用于主口播 PIP。

预览入口：`Layouts-Whiteboard-*`、`Layouts-Screen-*`、`Combinations-Whiteboard-PipRight-NumberedStepStack`。
