# 配色方案

动效模板只消费颜色角色，不拥有一套写死的品牌色。全片只选一个已注册 palette，由成片入口注入 `theme`。

色值来自 [Radix Colors](https://www.radix-ui.com/colors/docs/palette-composition/composing-a-palette) 的灰阶+强调配对，不是从口播视频取样发明的 hex。琥珀实心块必须用深色 `onAccent`。

当前四套：

| ID | 舞台 | 卡片 | 强调 | 兼容背景 |
|---|---|---|---|---|
| grid-hud-cyan@1 | dark | glass | 青 HUD | perspective-grid@1 |
| grid-cinema-amber@1 | dark | glass | 琥珀 | perspective-grid@1 |
| grid-neutral-gold@1 | dark | glass | 低彩金 | perspective-grid@1 |
| paper-day@1 | light | paper | 琥珀 | none |

`grid-hud-cyan@1` 是网格默认。选择顺序与人物口播呼应规则见 `references/color-planning.md`。
