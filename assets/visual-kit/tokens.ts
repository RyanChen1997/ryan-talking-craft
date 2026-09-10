export const MOTION_KIT_VERSION = "0.6.0";

export const FONT_STACK =
  'Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif';

export type MotionTheme = {
  background: string;
  surface: string;
  text: string;
  onSurface?: string;
  mutedText: string;
  mutedOnSurface?: string;
  line: string;
  primary: string;
  secondary: string;
  warning: string;
  success: string;
  mediaMatte?: string;
  onAccent?: string;
  captionText?: string;
  captionBackplate?: string;
  cardShadow?: string;
  fontFamily: string;
};

export type ThemeRoles = {
  onSurface: string;
  mutedOnSurface: string;
  onAccent: string;
  cardShadow: string;
  captionText: string;
  captionBackplate: string;
  mediaMatte: string;
};

/**
 * Resolve optional palette roles. Templates consume roles, never invent hex.
 */
export function themeRoles(theme: MotionTheme): ThemeRoles {
  return {
    onSurface: theme.onSurface ?? theme.text,
    mutedOnSurface: theme.mutedOnSurface ?? theme.mutedText,
    onAccent: theme.onAccent ?? "#FFFFFF",
    cardShadow: theme.cardShadow ?? "0 10px 28px rgba(0,0,0,0.18)",
    captionText: theme.captionText ?? "#FFFFFF",
    captionBackplate: theme.captionBackplate ?? "#101217",
    mediaMatte: theme.mediaMatte ?? "#15171C",
  };
}

export function colorWithAlpha(color: string, alpha: number): string {
  const clamped = Math.min(1, Math.max(0, alpha));
  const raw = color.trim().replace("#", "");
  const full = raw.length === 3 ? raw.split("").map((item) => `${item}${item}`).join("") : raw;
  if (full.length < 6 || raw.startsWith("rgb")) {
    return color.startsWith("rgb") ? color : `rgba(16,18,23,${clamped})`;
  }
  return `rgba(${Number.parseInt(full.slice(0, 2), 16)},${Number.parseInt(full.slice(2, 4), 16)},${Number.parseInt(full.slice(4, 6), 16)},${clamped})`;
}

export const timingAt30 = {
  keywordEnter: 6,
  fade: 8,
  highlight: 10,
  clickRing: 15,
  cameraMove: 12,
  stagger: 8,
} as const;

export const easing = {
  informationEnter: [0.16, 1, 0.3, 1] as const,
  camera: [0.65, 0, 0.35, 1] as const,
} as const;
