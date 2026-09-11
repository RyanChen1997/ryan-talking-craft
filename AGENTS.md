# Ryan Talking Craft

真人口播 Remotion 制作 skill 的源码仓库。制作时先确认内容，再取素材，再选布局 / 动效 / 配色。

## 0. Skill 引用与版本

- **目录引用规则**：AI Agent 处于本项目目录时，如无特殊提示，提到或使用 `ryan-talking-craft` 应直接读取当前项目中的 `SKILL.md`、`references/`、`scripts/` 和 `assets/`；不要改读用户级或其他项目级目录下的同名 skill。
- **版本记录规则**：该 skill 的唯一版本号记录在根目录 `pyproject.toml` 的 `[project].version` 中。其他文档或源码如需展示版本，必须以该字段为准，不能建立第二套版本来源。

## 1. 项目目录结构

`templates/` 下模板很多，这里不展开。`references/` 展开。

```text
ryan-talking-craft/
├── AGENTS.md                          # 给 Agent 的仓库导读（本文件）
├── SKILL.md                           # skill 入口：硬约束、阶段路由、制作流程
├── README.md                          # 仓库说明、预览与安装命令
├── install.sh                         # 把正式 skill 安装到用户 skills 目录
├── package.json                       # npm workspace，挂 preview
├── package-lock.json                  # npm 锁文件
├── pyproject.toml                     # Python 依赖（uv / pytest）
├── uv.lock                            # uv 锁文件
├── .gitignore                         # 忽略 node_modules、缓存、构建产物
│
├── references/                        # 制作时按阶段加载的规范
│   ├── workflow.md                    # 状态机、确认门禁、恢复与回退
│   ├── project-layout.md              # 成片工程目录与 spec 归属
│   ├── content-planning.md            # 字幕拆段、上屏文案、内容确认、内容确认稿格式
│   ├── video-understanding.md         # 抽帧、联系表、预算与缓存
│   ├── asset-management.md            # 定向搜素材、录制清单、来源责任
│   ├── visual-principles.md           # 该不该动、怎么选布局与模板
│   ├── visual-planning.md             # 画面方案：检索模板、写 visual 字段、画面确认稿格式
│   ├── color-planning.md              # 按背景和人物画面选注册配色
│   ├── media-layout.md                # 录屏完整 contain、人物 PIP 取景窗与比例失配取舍
│   ├── remotion-architecture.md       # 主 Composition、音轨、时间映射
│   ├── captions-and-audio.md          # 默认字幕、连续口播音轨
│   ├── data-contracts.md              # plan / assets / state 字段约定
│   └── qa-standards.md                # 分阶段检查与交付底线
│
├── assets/visual-kit/                 # 正式 skill 共享视觉库（会安装）
│   ├── README.md                      # 库边界、接入方式
│   ├── catalog.json                   # 模板 / 布局 / 背景 / 配色索引
│   ├── index.ts                       # 公开导出
│   ├── motion.ts                      # 公共运动工具
│   ├── tokens.ts                      # 颜色角色、字体、辅助函数
│   ├── types.ts                       # 公共类型
│   ├── templates/                     # 已晋级的动效模板（不展开）
│   ├── layouts/                       # 人物与内容空间布局
│   ├── background/                    # 舞台背景（当前透视网格）
│   ├── palettes/                      # 全片配色方案
│   └── runtime/                       # 字幕、口播音轨、录屏组件
│
├── preview/                           # 开发预览工程，不随 skill 安装
│   ├── README.md                      # 如何启动 Studio
│   ├── package.json                   # Remotion / React 依赖
│   ├── remotion.config.ts             # Remotion 配置
│   ├── tsconfig.json                  # TypeScript 配置
│   ├── palette-demo.html              # 配色静态对照页
│   ├── src/                           # Studio 入口与 Composition
│   └── public/                        # 预览专用素材
│
├── scripts/                           # 确定性脚本（安装后可用）
│   ├── __init__.py                    # 包标记
│   ├── common.py                      # 共用错误类型与写 JSON
│   ├── bootstrap_spec.py              # 创建 v2 spec 目录
│   ├── project_plan.py                # 确认稿、校验、状态流转
│   ├── extract_frames.py              # 抽帧
│   ├── build_video_contact_sheets.py  # 联系表
│   ├── build_keyframe_review.py       # 关键帧复核：按 plan 抽成片关键帧 + 低分辨率联系表
│   ├── inspect_media.py               # 媒体元数据
│   ├── convert_subtitles.py           # 字幕转 Caption JSON
│   ├── prepare_narration.py           # 口播转连续 WAV
│   ├── install_motion_kit.py          # 把 visual-kit 装进成片工程
│   ├── analyze_blank_regions.py       # 检查空白 / 露底
│   ├── analyze_frame_signal.py        # 帧级信号：素材运动量剖面、成片连续性、边缘出框
│   ├── analyze_motion_preview.py      # 检查短预览运动
│   ├── compare_goldens.py             # 对比 golden 帧
│   ├── run_visual_qa.py               # 视觉 QA 入口
│   ├── validate_design.py             # 旧格式设计校验（兼容）
│   ├── validate_motion_plan.py        # 旧格式动效计划校验（兼容）
│   ├── validate_timeline.py           # 旧格式时间轴校验（兼容）
│   └── validate_render.py             # 导出成片媒体检查
│
├── docs/                              # 仓库设计文档，不安装
│   ├── refactoring-plan.md            # 重构方案
│   ├── template-research-playbook.md  # 动效 / 布局研究怎么做
│   └── phase-one-status.md            # 第一轮实施记录
├── tests/                             # 脚本与安装测试，不安装
├── evals/                             # skill 触发评测用例
└── archive/                           # 旧规范与旧库快照；不安装、不预览、不 import
```

## 2. preview 与 skill 的关系

`preview/` 是开发验收台，不是安装产物。动效、布局、背景、配色等视觉件都先在 `preview` 里实现，人工审阅通过后，才写入正式 skill 的 `assets/visual-kit/`。

正常情况下，preview 与 skill 中的这些条目一一对应。未审阅通过的实现只留在 preview，不能当作成片默认候选。

## 3. 新增动效模板的规范

用户说“帮我加几个 XX 的动效模板”，就从本节第 3.1 条开始逐条走。下面几条不是建议，是本次踩过坑后定下的约束。

### 3.1 一个模板一条 Composition，配色不是模板的变体

**同一模板不得为不同 palette／舞台另开 Composition（例如 `-light` / `-dark` 两条）。** 模板接收注入的 `theme`（颜色角色），不接收 palette id，不写死 hex；全片只用一套注册配色，配色由成片级 `plan.palette` 决定。Studio 里配色走 props（`schema` + `defaultProps`），需要透视网格时根据 palette 的 `stage` 自动判断。

为什么：为每套配色开一条 Composition，等于把“机器确定的模板”和“按片确定的配色”绑成组合，既污染 Composition 列表，也会让人误以为模板有多个版本；新增一套配色就要回改所有模板。自查方法：两条 Composition 如果只有配色不同，就是重复条目，合并成一条。

### 3.2 一参考一模板，只摘动效本体

- 一个参考片对应一个模板；参考片 URL 写在 `Template.tsx` 头注释里（README 不写来源，也不另建来源／研究文档）。
- 摘取的是时序、缓动、错峰与 DOM 结构。参考作者的素材（照片、品牌图标、字体、配色、3D 实物）一律不进库，改成 props 或媒体槽。
- 参考画幅与成片画幅不同时**重排**，不拉伸、不裁切、不 cover；重排取舍写在 `Template.tsx` 的参数注释里，不另立文档。
- 不是所有动作都该移植：与表达无关的入场／装饰动作不要顺手带进来，也不要在制作时顺手改参考模板。

### 3.3 参考素材与抽帧纪律

- 只获取公开可访问内容，不绕过登录或权限控制。
- 下载脚本与全部中间产物（原片、字幕、抽帧、渲染样片）放 `.tmp/`，不进仓库、不进安装产物。
- 先读字幕与元数据、跑运动量剖面定位事件，再做抽帧；**提交给模型的必须是低分辨率图**（联系表或缩略图），原尺寸帧只在本机核对几何时用。
- 静态帧不能证明回弹、节奏与连续性。结论里分开写“观察到的”与“未确认的”，不要把抽帧推测说成看过动态。

### 3.4 落点、命名与晋级

1. 先实现到 `preview/src/templates/<carrier>/<relation>/<slug>/`（`Template.tsx` + `Preview.tsx` + `README.md`），注册一条 Composition 等用户审阅；未审阅不得写入正式库。全屏画面类模板用 `preview/src/shared/createFullscreenPreview.tsx`（整幅画布就是模板的舞台），嵌在舞台里的动效仍用 `createTemplatePreview`。
2. 审阅通过后，`Template.tsx` 与 `README.md` 平移进 `assets/visual-kit/templates/<carrier>/<relation>/<slug>/`，tokens 相对路径改成 `../../../../tokens`；preview 只留 `Preview.tsx` 与 README 副本，Template 的 import 指回正式库。
3. 同一轮必须一并改完：`catalog.json` 条目（`id` 为 `<slug>@1`）、`tests/test_visual_kit_catalog.py`（carrier 白名单与必查 id）、`SKILL.md` 与 `assets/visual-kit/README.md` 里的库目录清单。
4. 版本两处都要动，且只动这两处：skill 版本在 `pyproject.toml`，kit 版本在 `assets/visual-kit/tokens.ts` 的 `MOTION_KIT_VERSION`。
5. 收尾跑 `npm run typecheck`、`pytest`，两个 Composition 各渲一遍并跑 `analyze_frame_signal.py continuity` / `edges`，最后 `./install.sh` 同步到用户 skills 目录。

### 3.5 模板 README 只写现场信息

只写 `ID`、`适用场景`、`动效描述`，必要时加 `空间需求`、`强调色边界`。不写来源与验证状态、不写接入示例。

### 3.6 修改已有模板

模板是已验证资产：制作过程中不顺手改参考模板，要改先在本节流程里走一遍（preview 实现 → 审阅 → 同步晋级）。改动影响已确认画面时，回退到对应阶段重新确认。
