from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from common import TalkingCraftError, run_command, sha256_file, write_json


@dataclass(frozen=True)
class NarrationPrepConfig:
    sample_rate: int = 48_000
    channels: int = 1
    max_duration_delta_ms: float = 50.0
    max_packet_gap_ms: float = 2.0


_DEFAULT_CONFIG = NarrationPrepConfig()


@dataclass(frozen=True)
class NarrationPrepReport:
    passed: bool
    input_path: Path
    output_path: Path
    output_sha256: str
    codec: str
    sample_rate: int
    channels: int
    start_time_seconds: float
    duration_seconds: float
    source_duration_seconds: float | None
    duration_delta_ms: float | None
    max_packet_gap_ms: float
    issue: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "input_path": str(self.input_path),
            "output_path": str(self.output_path),
            "output_sha256": self.output_sha256,
            "codec": self.codec,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "start_time_seconds": self.start_time_seconds,
            "duration_seconds": self.duration_seconds,
            "source_duration_seconds": self.source_duration_seconds,
            "duration_delta_ms": self.duration_delta_ms,
            "max_packet_gap_ms": self.max_packet_gap_ms,
            "issue": self.issue,
        }


def prepare_narration(
    input_path: Path,
    output_path: Path,
    *,
    config: NarrationPrepConfig = _DEFAULT_CONFIG,
) -> NarrationPrepReport:
    """Create a browser-stable PCM WAV with continuous timestamps."""
    source = input_path.expanduser().resolve()
    output = output_path.expanduser().resolve()
    if not source.is_file():
        raise TalkingCraftError(f"Narration input does not exist: {source}")
    if output.suffix.lower() != ".wav":
        raise TalkingCraftError("Narration output must use the .wav extension")
    if config.sample_rate <= 0 or config.channels not in {1, 2}:
        raise TalkingCraftError("sample_rate must be positive and channels must be 1 or 2")
    output.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        (
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-fflags",
            "+genpts",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-af",
            f"aresample={config.sample_rate}:async=1:first_pts=0,asetpts=N/SR/TB",
            "-ar",
            str(config.sample_rate),
            "-ac",
            str(config.channels),
            "-c:a",
            "pcm_s16le",
            "-y",
            str(output),
        )
    )
    source_duration = _probe_audio_stream(source).get("duration")
    output_stream = _probe_audio_stream(output)
    output_duration = _required_float(output_stream.get("duration"), "duration")
    output_start = _float_or_zero(output_stream.get("start_time"))
    duration_delta_ms = (
        abs(output_duration - float(source_duration)) * 1000
        if source_duration is not None
        else None
    )
    max_packet_gap_ms = _max_packet_gap_ms(output)
    codec = str(output_stream.get("codec_name") or "")
    sample_rate = int(output_stream.get("sample_rate") or 0)
    channels = int(output_stream.get("channels") or 0)
    problems: list[str] = []
    if codec != "pcm_s16le":
        problems.append(f"unexpected codec {codec!r}")
    if sample_rate != config.sample_rate:
        problems.append(f"unexpected sample rate {sample_rate}")
    if channels != config.channels:
        problems.append(f"unexpected channel count {channels}")
    if abs(output_start) > 0.001:
        problems.append(f"non-zero start time {output_start:.6f}s")
    if duration_delta_ms is not None and duration_delta_ms > config.max_duration_delta_ms:
        problems.append(f"duration changed by {duration_delta_ms:.1f}ms")
    if max_packet_gap_ms > config.max_packet_gap_ms:
        problems.append(f"packet timeline gap is {max_packet_gap_ms:.3f}ms")
    return NarrationPrepReport(
        passed=not problems,
        input_path=source,
        output_path=output,
        output_sha256=sha256_file(output),
        codec=codec,
        sample_rate=sample_rate,
        channels=channels,
        start_time_seconds=output_start,
        duration_seconds=output_duration,
        source_duration_seconds=float(source_duration) if source_duration is not None else None,
        duration_delta_ms=duration_delta_ms,
        max_packet_gap_ms=max_packet_gap_ms,
        issue="; ".join(problems) if problems else None,
    )


def _probe_audio_stream(path: Path) -> dict[str, object]:
    result = run_command(
        (
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name,sample_rate,channels,start_time,duration",
            "-of",
            "json",
            str(path),
        )
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams", [])
    if not isinstance(streams, list) or not streams:
        raise TalkingCraftError(f"No audio stream found in {path}")
    stream = streams[0]
    if not isinstance(stream, dict):
        raise TalkingCraftError(f"Invalid ffprobe audio stream for {path}")
    return stream


def _max_packet_gap_ms(path: Path) -> float:
    result = run_command(
        (
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_packets",
            "-show_entries",
            "packet=pts_time,duration_time",
            "-of",
            "json",
            str(path),
        )
    )
    payload = json.loads(result.stdout)
    packets = payload.get("packets", [])
    previous_end: float | None = None
    maximum = 0.0
    for packet in packets if isinstance(packets, list) else []:
        if not isinstance(packet, dict):
            continue
        pts = _optional_float(packet.get("pts_time"))
        duration = _optional_float(packet.get("duration_time"))
        if pts is None or duration is None:
            continue
        if previous_end is not None:
            maximum = max(maximum, abs(pts - previous_end) * 1000)
        previous_end = pts + duration
    return maximum


def _required_float(value: object, label: str) -> float:
    parsed = _optional_float(value)
    if parsed is None:
        raise TalkingCraftError(f"ffprobe did not return audio {label}")
    return parsed


def _optional_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _float_or_zero(value: object) -> float:
    parsed = _optional_float(value)
    return parsed if parsed is not None else 0.0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare continuous 48kHz PCM narration for Remotion Studio"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sample-rate", type=int, default=48_000)
    parser.add_argument("--channels", type=int, choices=(1, 2), default=1)
    parser.add_argument("--output-report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = prepare_narration(
            args.input,
            args.output,
            config=NarrationPrepConfig(
                sample_rate=args.sample_rate,
                channels=args.channels,
            ),
        )
    except (TalkingCraftError, json.JSONDecodeError) as error:
        print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        return 2
    payload = report.to_dict()
    if args.output_report:
        write_json(args.output_report, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
