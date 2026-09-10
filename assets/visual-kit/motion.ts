import {Easing, interpolate} from "remotion";

export const enterProgress = (frame: number, duration: number): number => {
  return interpolate(frame, [0, Math.max(1, duration)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
};

export const staggerProgress = (
  frame: number,
  index: number,
  duration: number,
  stagger: number,
): number => enterProgress(frame - index * stagger, duration);

export const progressBetween = (
  frame: number,
  startFrame: number,
  endFrame: number,
): number =>
  interpolate(frame, [startFrame, Math.max(startFrame + 1, endFrame)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

export const exitProgress = (
  frame: number,
  startFrame: number,
  endFrame: number,
): number => 1 - progressBetween(frame, startFrame, endFrame);

export const clampCameraTranslation = (
  requested: number,
  stageSize: number,
  zoom: number,
): number => {
  const overscan = Math.max(0, (stageSize * (zoom - 1)) / 2);
  return Math.min(overscan, Math.max(-overscan, requested));
};
