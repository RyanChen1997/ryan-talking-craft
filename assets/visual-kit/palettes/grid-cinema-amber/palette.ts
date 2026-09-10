import {FONT_STACK, type MotionTheme} from "../../tokens";
import type {Palette} from "../types";

/** Radix sand + amber. Amber 9/10 need dark foreground text. */
export const theme: MotionTheme = {
  background: "#08080A",
  surface: "#222221",
  text: "#eeeeec",
  onSurface: "#eeeeec",
  mutedText: "#b5b3ad",
  mutedOnSurface: "#b5b3ad",
  line: "#3b3a37",
  primary: "#ffca16",
  secondary: "#cbb99f",
  warning: "#e54d2e",
  success: "#1fd8a4",
  mediaMatte: "#0B0B0E",
  onAccent: "#16120c",
  captionText: "#eeeeec",
  captionBackplate: "#111110",
  cardShadow: "0 16px 40px rgba(0,0,0,0.45)",
  fontFamily: FONT_STACK,
};

export const palette: Palette = {
  id: "grid-cinema-amber@1",
  stage: "dark",
  accentFamily: "warm",
  cardTreatment: "glass",
  compatibleBackgrounds: ["perspective-grid@1"],
  theme,
};
