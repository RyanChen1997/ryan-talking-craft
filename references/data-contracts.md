# v2 数据契约

所有文件 schema_version=2。plan.json 与 assets.json 是权威数据，确认 Markdown 是生成视图。v1 项目不自动迁移；历史资料归档在源码仓库，不是运行时依赖。

## plan.json 示例

```json
{
  "schema_version": 2,
  "slug": "demo",
  "title": "工具演示",
  "output": {"width": 1920, "height": 1080},
  "fps": 30,
  "duration_frames": 300,
  "captions": true,
  "background": "perspective-grid@1",
  "palette": "grid-hud-cyan@1",
  "segments": [{
    "id": "s1", "from": 0, "to": 300,
    "meaning": "展示实际输出", "screen_text": ["一次生成"],
    "asset_ids": ["demo"],
    "visual": {
      "layout": "screen-full@1", "template": null,
      "beats": "结果出现后保持完整画面",
      "clips": [{"asset_id": "demo", "source_in": 2, "source_out": 12, "fit": "contain", "zoom": 1}]
    }
  }]
}
```

`output.width` / `output.height` 是成片画布尺寸。初始化默认写入 1920×1080（16:9）；只有用户明确指定其他比例或尺寸时才修改，不能从任一输入媒体的宽高比推导覆盖。

from/to 是成片帧，半开区间，无间隙与重叠。source_in/source_out 是源秒。内容阶段可暂缺 duration_frames、visual、palette；画面确认前必须补全音轨总时长、布局、全片 `background` 与 `palette`。screen_text 可为空，不代表禁用字幕。clips 源范围不是变速许可，实现中另检查片段时长与成片对齐。`background`／`palette` 是全片字段，必须是当前 catalog 中的 id。`visual.layout` 必须是 catalog 中的布局 id，例如 `whiteboard-pip-right@1`、`screen-full@1`。

## assets.json 示例

```json
{
  "schema_version": 2,
  "assets": [{
    "id": "demo", "kind": "user_recording", "provider": "user",
    "purpose": "证明输出过程", "required": true, "status": "missing",
    "recording_request": {
      "content": "从输入页开始，提交内容，等待结果出现；前后各停留两秒",
      "record_seconds": 18, "use_seconds": 10
    }
  }]
}
```

ready 后添加 path、视频 duration_seconds、必要来源与隐私处理记录。用户录屏和演示 kind=user_recording；主口播 talking_head；静态图片 image。来源责任 provider 为 existing、user 或 ai。普通图片交付要求不需要虚构录制秒数。

AI 素材可补 search_budget、acceptance、source_url 等追溯字段。改变 purpose/provider/recording_request 会使内容批准失效；更新就绪状态与实际路径不会取消内容批准，但会影响画面批准。

## state.json 与 QA

状态与批准由 project_plan.py 管理，不手工伪造批准。blocking_reasons 可记录素材或制作阻塞。批准包含用户原话与数据哈希；更改内容用 reset 回退。

qa 报告约定见 qa-standards.md。当前结构检查不是完整 JSON Schema 验证，也不代替语义、文件和画面检查。
