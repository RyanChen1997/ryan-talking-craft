# 工作流与恢复

v2 状态：INTAKE → CONTENT_REVIEW → ACQUIRING_ASSETS → VISUAL_REVIEW → BUILDING → PREVIEW_REVIEW → FINAL_RENDER → DONE。

入口脚本：`uv run --project <skill-dir> --no-dev python <skill-dir>/scripts/project_plan.py <spec-dir> <action>`。

- `reviews`：从 plan/assets 生成两份确认视图，不改变状态。
- `validate`：内容结构与录制需求校验；`--visual` 增加布局、全片背景／配色、素材就绪和总时长检查。
- `advance --target <状态>`：仅允许相邻状态。进入素材获取、制作和正式导出必须附 `--user-message '<用户原话>'`。
- `hash --visual`：取得计划与素材的校验指纹，供 QA 报告绑定。
- `reset --target INTAKE`：内容变化后清除全部批准，重新确认。
- `reset --target ACQUIRING_ASSETS`：保留仍有效的内容批准，重做画面确认。

批准绑定内容指纹，素材就绪状态变化不会取消内容批准；改变表达、录制要求或素材用途会失效。画面批准绑定完整计划与素材，包含全片 background 与 palette。脚本校验结构与批准记录，不能替代人类真实确认或判断语义是否忠实。

缺素材不增加空文档，保持 ACQUIRING_ASSETS 并更新 blocking_reasons。遇到 schema v1 保留原文件，不自动覆盖；经确认建立独立 v2 spec，不以历史文档驱动新制作。v2 初始化与 v1 文件混用应报错。
