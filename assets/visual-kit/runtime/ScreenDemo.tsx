import React from "react";
import {Video} from "@remotion/media";
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from "remotion";
import {enterProgress} from "../motion";
import {DEFAULT_PALETTE_ID, resolvePalette} from "../palettes";
import {themeRoles} from "../tokens";
import type {EmptySpaceStrategy, ThemeProps} from "../types";

export type ScreenDemoProps = ThemeProps & {
  src: string;
  sourceStartFrame?: number;
  fit?: "contain";
  framed?: boolean;
  label?: string;
  emptySpaceStrategy?: EmptySpaceStrategy;
};

export const ScreenDemo: React.FC<ScreenDemoProps> = ({
  src,
  sourceStartFrame = 0,
  fit = "contain",
  framed = false,
  label,
  emptySpaceStrategy = "designed_matte",
  theme = resolvePalette(DEFAULT_PALETTE_ID).theme,
}) => {
  if (fit !== "contain") {
    throw new Error("ScreenDemo preserves the complete source frame; fit must be contain");
  }
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const roles = themeRoles(theme);
  const progress = enterProgress(frame, Math.round(fps * 0.25));
  const insetX = framed ? width * 0.055 : 0;
  const insetY = framed ? height * 0.06 : 0;

  return (
    <AbsoluteFill style={{backgroundColor: theme.background, fontFamily: theme.fontFamily}}>
      <div
        style={{
          position: "absolute",
          left: insetX,
          top: insetY,
          width: width - insetX * 2,
          height: height - insetY * 2,
          borderRadius: 0,
          overflow: "visible",
          border: framed ? `2px solid ${theme.line}` : "none",
          backgroundColor: roles.mediaMatte,
          boxShadow: framed ? roles.cardShadow : "none",
          opacity: progress,
        }}
      >
        <Video
          src={src}
          muted
          trimBefore={sourceStartFrame}
          objectFit={fit}
          data-qa-role="main-media"
          data-qa-id="screen-demo"
          data-qa-media-fit={fit}
          data-qa-empty-space-strategy={fit === "contain" ? emptySpaceStrategy : "none"}
          style={{width: "100%", height: "100%"}}
        />
      </div>
      {label ? (
        <div
          data-qa-role="source"
          data-qa-id="screen-demo-label"
          data-qa-avoid="face,gesture,caption,ui-target"
          style={{
            position: "absolute",
            left: Math.round(width * 0.045),
            top: Math.round(height * 0.035),
            padding: `${Math.round(height * 0.011)}px ${Math.round(width * 0.012)}px`,
            borderRadius: 999,
            backgroundColor: theme.surface,
            border: `2px solid ${theme.line}`,
            color: roles.onSurface,
            fontSize: Math.round(height * 0.023),
            fontWeight: 700,
          }}
        >
          {label}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
