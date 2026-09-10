from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from common import TalkingCraftError, write_json

_TIMESTAMP_PATTERN = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>(?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{3})"
)
_SPLIT_AFTER_PATTERN = re.compile(r"(?<=[，。！？；,.!?;：:])")
_TAG_PATTERN = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class CaptionCue:
    text: str
    start_ms: int
    end_ms: int
    timestamp_ms: int | None = None
    confidence: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "startMs": self.start_ms,
            "endMs": self.end_ms,
            "timestampMs": self.timestamp_ms,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class SubtitleConfig:
    max_chars: int = 18


_DEFAULT_CONFIG = SubtitleConfig()


def convert_subtitles(
    input_path: Path,
    *,
    config: SubtitleConfig = _DEFAULT_CONFIG,
) -> tuple[CaptionCue, ...]:
    """Convert SRT or VTT cues into bounded Remotion Caption-compatible cues."""
    if config.max_chars < 4:
        raise TalkingCraftError("max_chars must be at least 4")
    resolved = input_path.expanduser().resolve()
    if not resolved.is_file():
        raise TalkingCraftError(f"Subtitle file does not exist: {resolved}")
    raw_cues = _parse_timed_text(resolved.read_text(encoding="utf-8-sig"))
    result: list[CaptionCue] = []
    for cue in raw_cues:
        parts = _split_caption(cue.text, config.max_chars)
        result.extend(_allocate_timing(cue, parts))
    if not result:
        raise TalkingCraftError("Subtitle file contains no timed cues")
    return tuple(result)


def _parse_timed_text(text: str) -> tuple[CaptionCue, ...]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cues: list[CaptionCue] = []
    index = 0
    while index < len(lines):
        match = _TIMESTAMP_PATTERN.search(lines[index])
        if not match:
            index += 1
            continue
        start_ms = _timestamp_to_ms(match.group("start"))
        end_ms = _timestamp_to_ms(match.group("end"))
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1
        caption_text = _TAG_PATTERN.sub("", " ".join(text_lines)).strip()
        if caption_text and end_ms > start_ms:
            cues.append(CaptionCue(caption_text, start_ms, end_ms))
    return tuple(cues)


def _timestamp_to_ms(value: str) -> int:
    normalized = value.replace(",", ".")
    parts = normalized.split(":")
    hours_text, minutes_text, seconds_text = (
        parts if len(parts) == 3 else ("0", parts[0], parts[1])
    )
    seconds, milliseconds = seconds_text.split(".")
    return (
        int(hours_text) * 3_600_000
        + int(minutes_text) * 60_000
        + int(seconds) * 1_000
        + int(milliseconds)
    )


def _split_caption(text: str, max_chars: int) -> tuple[str, ...]:
    clauses = [part.strip() for part in _SPLIT_AFTER_PATTERN.split(text) if part.strip()]
    parts: list[str] = []
    pending = ""
    for clause in clauses:
        candidate = f"{pending}{clause}" if pending else clause
        if _visual_length(candidate) <= max_chars:
            pending = candidate
            continue
        if pending:
            parts.append(pending)
            pending = ""
        parts.extend(_split_long_clause(clause, max_chars))
    if pending:
        parts.append(pending)
    return tuple(parts or [text])


def _split_long_clause(text: str, max_chars: int) -> list[str]:
    words = text.split()
    if len(words) > 1:
        result: list[str] = []
        pending = ""
        for word in words:
            candidate = f"{pending} {word}".strip()
            if pending and _visual_length(candidate) > max_chars:
                result.append(pending)
                pending = word
            else:
                pending = candidate
        if pending:
            result.append(pending)
        return result
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]


def _visual_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _allocate_timing(cue: CaptionCue, parts: tuple[str, ...]) -> list[CaptionCue]:
    if len(parts) == 1:
        return [CaptionCue(parts[0], cue.start_ms, cue.end_ms)]
    weights = [max(_visual_length(part), 1) for part in parts]
    total_weight = sum(weights)
    total_duration = cue.end_ms - cue.start_ms
    result: list[CaptionCue] = []
    elapsed_weight = 0
    for index, (part, weight) in enumerate(zip(parts, weights, strict=True)):
        start_ms = cue.start_ms + round(total_duration * elapsed_weight / total_weight)
        elapsed_weight += weight
        end_ms = (
            cue.end_ms
            if index == len(parts) - 1
            else cue.start_ms + round(total_duration * elapsed_weight / total_weight)
        )
        result.append(CaptionCue(part, start_ms, max(start_ms + 1, end_ms)))
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert SRT/VTT to Remotion Caption-compatible JSON"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-chars", type=int, default=18)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        cues = convert_subtitles(
            args.input,
            config=SubtitleConfig(max_chars=args.max_chars),
        )
    except TalkingCraftError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2
    payload = [cue.to_dict() for cue in cues]
    write_json(args.output, payload)
    print(
        json.dumps(
            {"ok": True, "cue_count": len(cues), "output": str(args.output)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
