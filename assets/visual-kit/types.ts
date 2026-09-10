import type {MotionTheme} from "./tokens";

export type PresenterMode = "HIDDEN" | "SMALL" | "MEDIUM";
export type HorizontalSide = "left" | "right";
export type EmptySpaceStrategy =
  | "none"
  | "designed_matte"
  | "adjacent_content"
  | "blurred_backdrop";

export type NormalizedRect = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type ThemeProps = {
  theme?: MotionTheme;
};

export type QARole =
  | "title"
  | "body"
  | "caption"
  | "source"
  | "face"
  | "gesture"
  | "ui-target"
  | "main-media"
  | "pip";
