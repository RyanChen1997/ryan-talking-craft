# 工程目录

skill 仓库包含 SKILL.md、references、scripts、assets/visual-kit；preview、docs、tests 是开发侧资料。

实际成片工程：

```text
src/                       # 主入口、轨道、场景、motion-library
public/                    # 渲染需要的媒体，不覆盖原始素材
spec/<slug>/
  plan.json                # v2 权威计划，逐阶段补全
  assets.json              # 素材与需求
  state.json               # 阶段、批准与阻塞
  content-review.md         # 生成视图
  visual-review.md          # 生成视图
  qa/                      # 检查证据
.cache/talking-craft/       # 帧图、联系表等可重建缓存
out/                       # 局部片段与最终成片
```

只对 spec 增加 slug 层，不嵌套新的 Remotion 工程。图像分析缓存不自动复制到 public。确认稿来自计划，不手工双写。

初始生成仅 plan、assets、state 与 qa 目录。schema v1 不自动迁移；经用户确认后建立独立 v2 spec，不加载旧规范作为运行时依赖。
