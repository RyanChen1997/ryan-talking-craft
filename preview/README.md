# 独立模板与布局预览

在仓库根运行 `npm ci && npm run preview`。通过 npm workspace 直接引用 `assets/visual-kit`，不复制正式库实现，也不引用 `archive/`。

## 目录（与 assets/visual-kit 对齐）

```text
preview/src/
├── templates/          # 正式模板的 Studio Preview.tsx（实现在 assets/visual-kit）
│                       # 待审阅模板的 Template.tsx + README.md 也先放这里，审阅通过后整体平移进正式库
├── layouts/            # 正式布局的 Studio Preview.tsx（实现在 assets/visual-kit）
├── combinations/       # 布局 + 模板组合样片
└── shared/             # 预览共用（Backdrop、settings、createTemplatePreview、createFullscreenPreview）
```

待审阅实现放在与目标正式分类一致的 `preview/src/templates/` 路径，并注册到对应 Templates 分类。用户确认前不复制到 `assets/visual-kit/`、不写入 catalog。

正式模板实现在 `assets/visual-kit/templates/`；布局实现在 `assets/visual-kit/layouts/stage/`。`preview/src/.../Preview.tsx` 只负责 Studio 预览入口。未审阅条目不得留在正式库，也不得当作默认候选。

## 两种预览包裹方式

- `createTemplatePreview`：给 960×540 的**纸面画框**，适合嵌在舞台与布局里的动效模板。
- `createFullscreenPreview`：整幅画布就是模板自己的舞台（背景、卡片、版面都归模板），按 palette 注入 `theme`；深色舞台配色自动叠透视网格背景。**全屏画面类模板用这个。**

全屏模板只注册一个 Composition，配色在 Studio 的 props 面板里切（`schema` + `defaultProps`）——模板接收的是 `theme` 角色，不是某套固定配色，所以不给每套配色另开一条 Composition。

## Studio 入口

- **Backgrounds / Palettes**：背景、配色对照
- **Templates → Typography / MediaDisplay / Diagram**：已审阅动效（emphasis、kinetic-type、before-after、data-chart）；前后对比两条按 palette props 切换浅／深舞台
- **Templates → Typography → BeforeAfter / MediaDisplay → BeforeAfter**：前后对比模板（已晋级正式库）
- **Layouts → Whiteboard / Screen**：白板左／右 PIP、录屏全屏、录屏 + 左／右 PIP
- **Combinations**：白板 + 右 PIP + 编号步骤堆

Composition 命名：`Templates-{Carrier}-{Relation}-{slug}`。
