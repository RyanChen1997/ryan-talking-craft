# 字幕与音轨

默认字幕开启，明确 opt-out 才关闭并保留原话。字幕颜色跟随全片 palette 的 caption 角色；底色默认不透明度 0.18，去掉厚重底板阴影；CaptionOverlay 的 backgroundOpacity 可在 0～1 调整，0 为完全透明。在浅色录屏上实际检查对比度，不擅自恢复厚重黑条。convert_subtitles.py 生成 Caption JSON；CaptionOverlay 全片挂载，不能按分镜反复挂载。

prepare_narration.py 将主口播规范化为 48kHz 连续 PTS 的 PCM WAV。NarrationTrack 顶层只挂一次；其他素材静音。成片 duration_frames=round(最终音轨秒数×fps)，不是字幕最后一句。

用户原音视频只读，不用 stream-copy 异常 AAC 时间戳作为连续主轨。代理写新路径。删改后的音轨、字幕和真人视觉使用同一编辑映射。

检查开头、中段跨切镜和结尾的正常速度播放；卡顿、重复、爆音或追赶均需修复，不用元数据检查代替听觉验证。检查连续 PTS、采样率、解码和唯一音轨，并将排障证据写入当前 qa 目录，不依赖历史规范。
