# 独立模板与布局预览

在仓库根运行 `npm ci && npm run preview`。通过 npm workspace 直接引用 `assets/visual-kit`，不复制正式库实现，也不引用 `archive/`。

## 目录（与 assets/visual-kit 对齐）

```text
preview/src/
├── templates/          # 正式模板的 Studio Preview.tsx（实现在 assets/visual-kit）
├── layouts/            # 正式布局的 Studio Preview.tsx（实现在 assets/visual-kit）
├── combinations/       # 布局 + 模板组合样片
└── shared/             # 预览共用（Backdrop、settings、createTemplatePreview）
```

待审阅实现放在与目标正式分类一致的 `preview/src/templates/` 路径，并注册到对应 Templates 分类。用户确认前不复制到 `assets/visual-kit/`、不写入 catalog。

正式模板实现在 `assets/visual-kit/templates/`；布局实现在 `assets/visual-kit/layouts/stage/`。`preview/src/.../Preview.tsx` 只负责 Studio 预览入口。未审阅条目不得留在正式库，也不得当作默认候选。

## Studio 入口

- **Backgrounds / Palettes**：背景、配色对照
- **Templates → Typography / Diagram**：已审阅动效（emphasis、kinetic-type、data-chart）
- **Layouts → Whiteboard / Screen**：白板左／右 PIP、录屏全屏、录屏 + 左／右 PIP
- **Combinations**：白板 + 右 PIP + 编号步骤堆

Composition 命名：`Templates-{Carrier}-{Relation}-{slug}`。
