# 素材管理

每项素材有 id、purpose、provider（user/ai/existing）、status（missing/ready）、required 和 kind。用户录屏／演示片段用 kind=user_recording；真人主片用 talking_head。

用户需录制的视频必须填写 recording_request：content（起始状态、具体动作、结果）、record_seconds（建议原片秒数）、use_seconds（成片预计秒数）。非录制素材缺口要写具体交付要求，不伪装成录制任务。

AI 只对已批准需求搜索。先用户现有素材，再官方或原始来源；取得满足用途的素材即停。为每项记录搜索预算、合格条件、来源 URL、获取日期及授权／隐私边界。搜索失败则报告，不无限扩大范围或生成假 UI。

ready 素材记录 path、duration_seconds（视频）、来源。预览前实际检查文件存在、可解码与关键内容可读，不能仅把状态改成 ready。

用户视频允许时间剪辑、按真实语义重排独立操作；不允许造出并未发生的操作因果。完整画幅、contain、zoom=1 是展示硬约束，参见 media-layout.md。
