# Ryan Talking Craft

真人口播视频的内容优先制作 skill，以及独立 Remotion 模板／布局预览工程。

## 第一轮重构状态

- v2 流程：内容确认 → 定向素材获取 → 画面确认 → 制作 → QA／预览确认 → 正式导出。
- 最小 spec：plan.json、assets.json、state.json、qa/；两份确认稿自动生成。
- 用户录屏允许时间剪辑，禁止裁边、改变比例和局部放大。
- 分层抽帧与联系表缓存；默认图像长边 480 像素。
- assets/visual-kit 为共享源码；preview 只负责开发预览，不安装到 skill。
- 旧规范与旧动画归档到 archive/legacy，不进入正式库、预览或安装产物。

## 启动预览

需要 Node.js 与 npm：

```bash
npm ci
npm run preview
```

终端会打印实际端口。Studio 支持播放、暂停与拖动时间轴；通过右侧 Props 编辑背景、注册配色、测试文字和布局参数（若面板收起，在 Studio 中展开 Props）。

入口：

- Palette-Compare：四套注册配色对照，Props 切换 palette。静态对照页：`preview/palette-demo.html`。
- Templates：已审阅动效（Typography / Diagram，见 Studio 文件夹）。
- Layouts：白板左／右 PIP、录屏全屏（隐藏 PIP）、录屏 + 左／右 PIP。
- Combinations：白板 + PIP + 动效模板。
- Background-Grid / Background-Captions：网格背景与字幕。

新模板输入不写死文案。测试文字仅在 preview 中提供；结构模式用占位笔画观察运动。真实口播同步与最终审美需要另用用户素材验收，当前人物仅为占位图形。

## 安装用户级 skill

安装逻辑全部位于 `install.sh`，不调用 Python。默认安装到 `~/.pi/agent/skills/ryan-talking-craft`：

```bash
./install.sh --dry-run
./install.sh
# --skills-dir 是 skills 父目录，不是具体 skill 子目录
./install.sh --skills-dir ~/.agents/skills --dry-run
# 已存在时需要明确覆盖，自动保留带时间戳的备份
./install.sh --skills-dir ~/.agents/skills --force
```

安装白名单直接写在 `install.sh`：`SKILL.md`、`references/`、`scripts/`、`assets/visual-kit/`、`pyproject.toml`、`uv.lock`。其余顶层内容不安装；白名单目录内的 `.tmp`、缓存和 `node_modules` 也会清理。不会覆盖其他 skill。备份在目标 skills 目录下的 `.ryan-talking-craft-backup-*`。

本轮开发只在临时目录验证安装，没有覆盖本机已安装 skill。

## 使用与测试

AI 从 SKILL.md 读取阶段路由；字段与命令见 references/data-contracts.md 和 references/workflow.md。

```bash
uv run pytest -q
npm run typecheck
npm run preview:bundle
```

如果历史 `.venv` 已损坏，不必删除它，可使用独立 uv 环境：

```bash
UV_PROJECT_ENVIRONMENT=/tmp/ryan-talking-craft-refactor-env uv run pytest -q
```

默认创建 v2，拒绝与旧 spec 混用，尚未提供自动迁移工具。源码仓库的 archive/legacy 仅用于历史参考，不安装、不预览；低层脚本保留的 v1 接口仅为兼容测试，不是新制作入口。

## 文档

- [重构方案](docs/refactoring-plan.md)
- [模板与布局研究执行指南](docs/template-research-playbook.md)
- [第一轮实施记录](docs/phase-one-status.md)

已审阅动效以 `assets/visual-kit/catalog.json` 为准；未晋级条目不得当作制作默认候选。
