---
name: ryan-talking-craft
description: "真人口播视频制作：分析视频、字幕与已有素材，先确认精简上屏内容和录制需求，再定向获取素材、确认布局动效方案，用 Remotion 制作、验证、预览和导出。用户要求包装真人口播、给真人视频配动效或按口播脚本制作成片时使用。不要用于纯旁白、纯录屏、纯动画、封面或仅剪切转码。"
compatibility: "在用户 Remotion 工程根目录运行；需要 Node.js、uv、ffmpeg/ffprobe。公开素材获取可能需要浏览器。"
---

# Ryan Talking Craft

内容先于画面，使用成熟模板而非每条视频重新研究动画。先阅读现有 `spec/<slug>/state.json`，恢复工作，不重复已完成分析与确认。

## 硬约束

- 用户原始媒体只读；所有处理写到新路径。
- 真人口播主音轨连续、顶层挂载一次；真人与演示视频静音；音画共享成片到源时间映射。
- 默认成片为 16:9 横屏，输出 1920×1080；只有用户明确指定其他比例或尺寸时才改变，不从口播源视频、录屏或图片的画幅反推成片画幅。
- 默认显示字幕，仅用户明确要求无字幕时关闭。总时长以最终口播音轨为准，不以最后一句字幕为准。
- 用户录屏／辅助演示视频允许时间截取和不歪曲事实的片段重排，但禁止空间裁切、拉伸、改变宽高比、局部放大或推近。完整画面等比适配，不使用 cover；空间不足调整布局或隐藏人物。
- 分析用 ROI 不得当作成片裁切授权。主口播人物 PIP 单独遵守人脸与手势安全要求。
- 不伪造 UI、数据、操作或事实证据，不绕过访问权限。
- 内容确认前不展开外部素材搜索；画面确认前不全面制作；预览确认前不正式导出。
- 没有表达作用就不加动效；静态阅读合法，不强制变化频率或逐段自定义动画。

## 按阶段加载

| 阶段 | 参考 |
|---|---|
| 初始化、状态、恢复 | `references/workflow.md`、`references/project-layout.md` |
| 内容与录制需求 | `references/content-planning.md` |
| 视频视觉理解 | `references/video-understanding.md` |
| 素材采购、录制核对 | `references/asset-management.md` |
| 布局、模板与配色 | `references/visual-principles.md`、`references/visual-planning.md`、`references/color-planning.md`、候选模板／配色 README |
| 工程实现 | `references/remotion-architecture.md`、`references/media-layout.md`、`references/captions-and-audio.md` |
| 计划字段、检查 | `references/data-contracts.md`、`references/qa-standards.md` |

本 skill 运行时只使用 v2 规范和当前 catalog。旧项目不静默迁移；遇到 schema v1 时告知用户，确认后建立独立的 v2 spec。历史资料仅在源码仓库 archive/legacy 中保留，不随安装分发，不作为制作依赖。

## 执行流程

### 1. 初始化与内容确认

必需输入：真人口播视频、对应带时间码字幕。可选：脚本、图片、录屏、来源、用户指定画幅。未指定画幅时直接采用 1920×1080，不为此询问；只有用户明确提出其他比例或尺寸时覆盖默认值。仅缺失会改变事实或用户工作量的其他信息时询问。

从主题推导 slug，在当前成片工程运行：

```bash
uv run --project <skill-dir> --no-dev python <skill-dir>/scripts/bootstrap_spec.py \
  --root "$PWD" --slug <slug> --title '<标题>'
```

读取字幕，检查媒体元数据及少量联系表。填写 `plan.json` 的语义段落、最终上屏文字及素材引用，填写 `assets.json` 的用途、来源责任、已有状态和缺口。

用户需录制的每项素材写清：起始状态、操作、结果、建议录制秒数、成片预计使用秒数及隐私要求。此时不选模板、不写弹簧和逐帧动作。

运行 `project_plan.py <spec-dir> reviews` 和 `advance --target CONTENT_REVIEW`，向用户展示内容稿及素材需求，停止等待确认。确认后以用户原话运行 `advance --target ACQUIRING_ASSETS --user-message '<原话>'`，不能代替用户批准。

### 2. 定向获取与核对素材

仅围绕批准的需求获取素材。每项有合格条件、搜索预算、停止条件和失败处理。用户素材未齐时保持本阶段，在 state 的 blocking_reasons 记录，不伪造替代。

已有视频理解复用缓存；补充素材只分析相关时间段。更新路径、时长、来源与 ready 状态。内容或录制需求发生实质变化，回到内容确认。

### 3. 画面方案确认

先读画面编排原则，再按表达关系筛模板索引，只读候选说明与动态预览，不通看整个库。当前 visual-kit 收录 catalog 中 `status: reviewed` 的动效模板（typography/emphasis、typography/kinetic-type、diagram/data-chart）、五套舞台布局（白板左／右 PIP、录屏全屏、录屏 + 左／右 PIP）、默认网格背景和四套配色。只从 `assets/visual-kit/catalog.json` 选择，不得从归档中擅自加载旧组件，也不得使用未晋级的 preview staging。

逐段填写 visual：布局、模板、口播触发与关键展开顺序、媒体源时间范围。全片填写 `background` 与 `palette`：先定背景，再按 `color-planning.md` 用人物口播联系表从已注册方案里选一套，不写进模板，不现场发明 hex。稳定模板复用参数；允许无模板的静态画面。齐全后运行 `advance --target VISUAL_REVIEW`，展示生成的画面稿，必要时提供代表性小样，等待确认。

确认后运行 `advance --target BUILDING --user-message '<原话>'`。

### 4. 制作与验证

实现前读取当前可用的 Remotion 技能和对应 API 文档。共享视觉库从 `assets/visual-kit/` 接入，已有副本比较版本，不覆盖用户修改。

准备连续口播 WAV、字幕 JSON 和静音视觉素材。按批准计划制作，先验证局部动态再做全片检查。不要调用 v1 设计／时间轴校验器直接校验 v2 plan。

验证报告写入 `qa/production.json`，包含真实检查证据、passed 和当前 plan_hash；通过后进入 PREVIEW_REVIEW。报告不是视觉质量的自动证明，必须实际观看。对白板 + PIP 镜头至少检查一帧：人物确实由 `StageLayout.presenter` 的圆角容器裁切，关键文字与动效完整落在 `safe` 内容槽内，而不是按目测偏移。

### 5. 预览、导出与交付

启动 Studio，给出精确入口，等待用户预览。修改布局或文案后重新确认受影响方案并复测。

明确同意后进入 FINAL_RENDER，正式导出；运行媒体与最终画面检查，写 `qa/delivery.json` 后进入 DONE。

每次只回报：当前阶段、产物路径、实际完成的检查、阻塞和用户需要做的最小动作。不得将未运行的测试或未观看的动态预览称为通过。
