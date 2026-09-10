import React, {useId} from "react";
import {useCurrentFrame, useVideoConfig} from "remotion";

/**
 * PerspectiveGridBackground — the kit's default stage backdrop (since 0.6.0).
 *
 * Black canvas with a 3D-feel wireframe grid: vertical rays converge toward a
 * vanishing point far above the frame, horizontal lines are perspective-spaced
 * (denser near the horizon) and scroll slowly toward the viewer, wrapping
 * seamlessly off-screen. Deterministic — driven only by useCurrentFrame; no CSS
 * transition/animation, no random values.
 *
 * Real-time state duty: ambient spatial-depth texture requested as the kit-wide
 * default; it carries no semantic beat and stays visually subordinate
 * (slow speed, low line alpha). Pair with a dark-stage palette from
 * `palettes/` so text and cards use registered roles, not ad-hoc hex.
 *
 * Usage (composition root, behind the presenter column and all scenes):
 *   <AbsoluteFill style={{backgroundColor: resolvePalette(id).theme.background}}>
 *     <PerspectiveGridBackground />
 *     ...
 *   </AbsoluteFill>
 */

export type PerspectiveGridBackgroundProps = {
  /** Warm-white line color as "R, G, B" (no alpha). */
  lineRgb?: string;
  /** Horizontal-line scroll speed in lines per second (toward the viewer). */
  linesPerSecond?: number;
  /** Canvas color painted under the grid. */
  canvas?: string;
  /** Bottom-edge spacing between vertical rays in px at 1080p height. */
  verticalGap?: number;
};

export const PerspectiveGridBackground: React.FC<PerspectiveGridBackgroundProps> = ({
  lineRgb = "232, 228, 218",
  linesPerSecond = 0.8,
  canvas = "#08080A",
  verticalGap = 258,
}) => {
  const gradientId = useId();
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  if (!Number.isFinite(verticalGap) || verticalGap < 8 || !Number.isFinite(linesPerSecond)) {
    throw new Error('Grid requires verticalGap >= 8 and finite linesPerSecond');
  }
  const t = (frame / fps) * linesPerSecond;

  // Horizontal lines: y = VP_Y + C / d (small d = close to viewer = low on screen).
  const VP_Y = -Math.round(height * 1.39);
  const C = Math.round(height * 2.43);
  const H_STEP = 0.058;
  const H_COUNT = 20;
  const horizontals: {y: number; opacity: number}[] = [];
  for (let k = 0; k < H_COUNT; k++) {
    const wrapped = (((k - t) % H_COUNT) + H_COUNT) % H_COUNT;
    const d = 1.0 + wrapped * H_STEP;
    const y = VP_Y + C / d;
    if (y < -40 || y > height + 40) continue;
    const opacity = 0.1 + 0.26 * Math.min(1, Math.max(0, y / height));
    horizontals.push({y, opacity});
  }

  // Vertical rays from the vanishing point through evenly spaced bottom crossings.
  const rays: number[] = [];
  const jMin = Math.ceil((0 - width / 2) / verticalGap) - 1;
  const jMax = Math.floor((width - width / 2) / verticalGap) + 1;
  for (let j = jMin; j <= jMax; j++) {
    rays.push(width / 2 + j * verticalGap);
  }

  return (
    <div
      data-qa-role="background"
      data-qa-id="perspective-grid"
      style={{position: "absolute", inset: 0, overflow: "hidden", backgroundColor: canvas}}
    >
      <svg
        style={{position: "absolute", inset: 0}}
        width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={`rgb(${lineRgb})`} stopOpacity="0.05" />
            <stop offset="0.45" stopColor={`rgb(${lineRgb})`} stopOpacity="0.16" />
            <stop offset="1" stopColor={`rgb(${lineRgb})`} stopOpacity="0.3" />
          </linearGradient>
        </defs>
        <g stroke={`url(#${gradientId})`} strokeWidth={2}>
          {rays.map((x, i) => (
            <line key={`v${i}`} x1={width / 2} y1={VP_Y} x2={x} y2={height + 80} />
          ))}
        </g>
        <g stroke={`rgb(${lineRgb})`} strokeWidth={2}>
          {horizontals.map((h, i) => (
            <line
              key={`h${i}`}
              x1={0}
              y1={h.y}
              x2={width}
              y2={h.y}
              strokeOpacity={h.opacity}
            />
          ))}
        </g>
      </svg>
    </div>
  );
};
