import {FONT_STACK, type MotionTheme} from "../../tokens";
import type {Palette} from "../types";

/** Radix sand + gold. Low chroma; gold 9 takes white foreground. */
export const theme: MotionTheme = {
  background: "#08080A",
  surface: "#222221",
  text: "#eeeeec",
  onSurface: "#eeeeec",
  mutedText: "#b5b3ad",
  mutedOnSurface: "#b5b3ad",
  line: "#3b3a37",
  primary: "#cbb99f",
  secondary: "#978365",
  warning: "#ec6142",
  success: "#27b08b",
  mediaMatte: "#0B0B0E",
  onAccent: "#FFFFFF",
  captionText: "#eeeeec",
  captionBackplate: "#111110",
  cardShadow: "0 16px 40px rgba(0,0,0,0.45)",
  fontFamily: FONT_STACK,
};

export const palette: Palette = {
  id: "grid-neutral-gold@1",
  stage: "dark",
  accentFamily: "neutral",
  cardTreatment: "glass",
  compatibleBackgrounds: ["perspective-grid@1"],
  theme,
};
