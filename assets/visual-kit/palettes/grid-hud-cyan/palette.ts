import {FONT_STACK, type MotionTheme} from "../../tokens";
import type {Palette} from "../types";

/** Radix slate + cyan on the kit grid canvas. Cyan 9/11 take white foreground. */
export const theme: MotionTheme = {
  background: "#08080A",
  surface: "#212225",
  text: "#edeef0",
  onSurface: "#edeef0",
  mutedText: "#b0b4ba",
  mutedOnSurface: "#b0b4ba",
  line: "#363a3f",
  primary: "#4ccce6",
  secondary: "#0bd8b6",
  warning: "#ff977d",
  success: "#0bd8b6",
  mediaMatte: "#0B0B0E",
  onAccent: "#FFFFFF",
  captionText: "#edeef0",
  captionBackplate: "#111113",
  cardShadow: "0 16px 40px rgba(0,0,0,0.45)",
  fontFamily: FONT_STACK,
};

export const palette: Palette = {
  id: "grid-hud-cyan@1",
  stage: "dark",
  accentFamily: "cool",
  cardTreatment: "glass",
  compatibleBackgrounds: ["perspective-grid@1"],
  theme,
};
