# 配色选择

动效模板只控制展开方式，不拥有品牌色。全片只选一套已注册 palette，在画面方案里与背景一起确认。不要在模板里写死 hex，也不要从口播视频里取样后现场发明新方案。

这两句约束的对象不同，不要混：目标是库里的模板只消费 theme 角色、不写死 hex；而当前库中多数模板仍是演示语境形态，**摘取**到成片工程自己的场景组件时，把其中写死的字色／纸面／强调色映射到 theme 角色属适配，不算改配色、也不算违反本页；参考模板本身不改。制作侧仍然只能在已注册 palette 里选，不得为单段发明新 hex。

当前色值来自 [Radix Colors](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale)：灰阶 1–2 做底、3–5 做卡片、6–8 做线、9–10 做实心强调、11/12 做字。青/金实心块配白字；琥珀实心块配深色字。

## 何时选择

内容、布局和动效模板先定。背景确定之后，再读本页和 `assets/visual-kit/palettes/` 索引，选出一个 palette 写入 `plan.json` 的顶层 `palette`，并在画面确认稿里展示。不新增独立批准门禁；换背景或换配色都会使画面批准失效。

## 选择顺序

1. 看已选背景的舞台明暗。`perspective-grid@1` 是 dark。catalog 里 `compatibleBackgrounds` 对不上的方案直接排除。
2. 看口播人物联系表，只分类、不取色：衣服冷／暖／黑灰中性；衣服深／浅；室内光冷白还是钨丝暖黄。不要用皮肤当强调色。
3. 在剩余方案里按呼应规则挑一个。全片共用，不按段落换色。
4. 把候选 README 和 `Palette-Compare` 预览给自己核对对比度，再写入计划。用户确认画面方案时一并看到配色名称。开发对照页：`preview/palette-demo.html`。

## 呼应规则

- 衣服或房间偏黑、灰、蓝、冷白：`grid-hud-cyan@1`。这是网格背景的默认。青是暖白网格线的互补色。
- 衣服或灯光明显偏驼、棕、铁锈、暖黄：`grid-cinema-amber@1`。强调色跟服装／灯光家族，不跟皮肤。琥珀徽标必须用 `onAccent` 深字。
- 上屏文字偏多，或人物已经很花、希望卡片保持中性：`grid-neutral-gold@1`。低彩金，不把青或琥珀铺满。
- 明确不用网格、需要浅底：`paper-day@1`。不能和 `perspective-grid@1` 搭配。

人物画面再怎么取样，也只用来在上表里做选择。禁止输出一组新的 primary/secondary hex。

## 写入计划

`plan.background` 与 `plan.palette` 是全片字段，不是段落 visual 的一部分。制作时成片入口 `resolvePalette(plan.palette).theme` 注入模板、字幕和媒体组件。背景负责画布和装饰线；palette 负责字、卡片、强调和字幕色。

换背景后必须重选兼容配色。制作阶段不得为了好看改角色 hex。
