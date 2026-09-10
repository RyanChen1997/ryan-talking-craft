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
│   ├── public/                        # 预览专用素材
│   └── collected/                     # 待审阅的收集项（templates/ 不展开）
│
├── scripts/                           # 确定性脚本（安装后可用）
│   ├── __init__.py                    # 包标记
│   ├── common.py                      # 共用错误类型与写 JSON
│   ├── bootstrap_spec.py              # 创建 v2 spec 目录
│   ├── project_plan.py                # 确认稿、校验、状态流转
│   ├── extract_frames.py              # 抽帧
│   ├── build_video_contact_sheets.py  # 联系表
│   ├── inspect_media.py               # 媒体元数据
│   ├── convert_subtitles.py           # 字幕转 Caption JSON
│   ├── prepare_narration.py           # 口播转连续 WAV
│   ├── install_motion_kit.py          # 把 visual-kit 装进成片工程
│   ├── analyze_blank_regions.py       # 检查空白 / 露底
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
├── archive/                           # 旧规范与旧库快照；不安装、不预览、不 import
└── research/                          # 开发期研究记录（可空；不安装）
```

## 2. preview 与 skill 的关系

`preview/` 是开发验收台，不是安装产物。动效、布局、背景、配色等视觉件都先在 `preview` 里实现，人工审阅通过后，才写入正式 skill 的 `assets/visual-kit/`。

正常情况下，preview 与 skill 中的这些条目一一对应。未审阅通过的实现只留在 preview，不能当作成片默认候选。
