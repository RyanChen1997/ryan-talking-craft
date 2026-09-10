import React, {useCallback, useEffect, useMemo, useState} from "react";
import {
  AbsoluteFill,
  cancelRender,
  continueRender,
  delayRender,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {colorWithAlpha, themeRoles, type MotionTheme} from "../tokens";

export type CaptionCue = {
  text: string;
  startMs: number;
  endMs: number;
  timestampMs: number | null;
  confidence: number | null;
};

export type CaptionPlacement = "top-safe" | "bottom-safe";

export type CaptionPlacementOverride = {
  startFrame: number;
  endFrame: number;
  placement: CaptionPlacement;
};

export type CaptionOverlayProps = {
  src: string;
  placement?: CaptionPlacement;
  placementOverrides?: CaptionPlacementOverride[];
  fontSize?: number;
  maxLines?: 1 | 2;
  maxWidthRatio?: number;
  /** Backplate opacity: 0 is fully transparent, 1 is opaque. */
  backgroundOpacity?: number;
  theme?: MotionTheme;
};

const isCaptionCue = (value: unknown): value is CaptionCue => {
  if (!value || typeof value !== "object") {
    return false;
  }
  const cue = value as Partial<CaptionCue>;
  return (
    typeof cue.text === "string" &&
    typeof cue.startMs === "number" &&
    typeof cue.endMs === "number" &&
    cue.endMs > cue.startMs
  );
};

export const CaptionOverlay: React.FC<CaptionOverlayProps> = ({
  src,
  placement = "bottom-safe",
  placementOverrides = [],
  fontSize,
  maxLines = 2,
  maxWidthRatio = 0.82,
  backgroundOpacity = 0.18,
  theme,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const [handle] = useState(() => delayRender("Loading talking-head captions"));
  const [captions, setCaptions] = useState<CaptionCue[] | null>(null);

  const load = useCallback(async () => {
    const response = await fetch(src);
    if (!response.ok) {
      throw new Error(`Could not load captions: ${response.status} ${response.statusText}`);
    }
    const payload: unknown = await response.json();
    if (!Array.isArray(payload) || !payload.every(isCaptionCue)) {
      throw new Error("Caption JSON must be an array of Caption-compatible cues");
    }
    setCaptions(payload);
    continueRender(handle);
  }, [handle, src]);

  useEffect(() => {
    load().catch((error: unknown) => cancelRender(error));
  }, [load]);

  const currentTimeMs = (frame / fps) * 1000;
  const active = useMemo(
    () => captions?.find((cue) => cue.startMs <= currentTimeMs && cue.endMs > currentTimeMs),
    [captions, currentTimeMs],
  );
  if (!active) {
    return null;
  }

  const activePlacement =
    placementOverrides.find(
      (override) => override.startFrame <= frame && override.endFrame > frame,
    )?.placement ?? placement;
  const portrait = height > width;
  const safeOffset = portrait ? height * 0.105 : height * 0.075;
  const resolvedFontSize = fontSize ?? Math.round(height * (portrait ? 0.032 : 0.041));
  const roles = theme ? themeRoles(theme) : null;

  return (
    <AbsoluteFill
      style={{
        zIndex: 1000,
        pointerEvents: "none",
        alignItems: "center",
        justifyContent: activePlacement === "top-safe" ? "flex-start" : "flex-end",
        paddingTop: activePlacement === "top-safe" ? safeOffset : 0,
        paddingBottom: activePlacement === "bottom-safe" ? safeOffset : 0,
      }}
    >
      <div
        data-qa-role="caption"
        data-qa-id="primary-caption"
        data-qa-avoid="face,gesture,source,ui-target"
        style={{
          maxWidth: `${Math.min(Math.max(maxWidthRatio, 0.5), 0.92) * 100}%`,
          padding: `${Math.round(height * 0.012)}px ${Math.round(width * 0.018)}px`,
          borderRadius: Math.round(height * 0.014),
          backgroundColor: colorWithAlpha(roles?.captionBackplate ?? "#101217", backgroundOpacity),
          boxShadow: "none",
          color: roles?.captionText ?? "#FFFFFF",
          fontFamily: theme?.fontFamily ?? 'Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif',
          fontSize: resolvedFontSize,
          fontWeight: 750,
          lineHeight: 1.28,
          letterSpacing: "0.01em",
          textAlign: "center",
          textShadow: "0 2px 4px rgba(0,0,0,0.55)",
          whiteSpace: "pre-wrap",
          overflow: "hidden",
          display: "-webkit-box",
          WebkitBoxOrient: "vertical",
          WebkitLineClamp: maxLines,
        }}
      >
        {active.text}
      </div>
    </AbsoluteFill>
  );
};
