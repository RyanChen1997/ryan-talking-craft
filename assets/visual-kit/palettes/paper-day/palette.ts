import {FONT_STACK, type MotionTheme} from "../../tokens";
import type {Palette} from "../types";

/** Radix sand + amber on a light stage. Amber 9 needs dark foreground. */
export const theme: MotionTheme = {
  background: "#f9f9f8",
  surface: "#ffffff",
  text: "#21201c",
  onSurface: "#21201c",
  mutedText: "#63635e",
  mutedOnSurface: "#63635e",
  line: "#dad9d6",
  primary: "#ffc53d",
  secondary: "#ab6400",
  warning: "#e54d2e",
  success: "#30a46c",
  mediaMatte: "#15171C",
  onAccent: "#4f3422",
  captionText: "#ffffff",
  captionBackplate: "#111110",
  cardShadow: "0 10px 28px rgba(33,32,28,0.08)",
  fontFamily: FONT_STACK,
};

export const palette: Palette = {
  id: "paper-day@1",
  stage: "light",
  accentFamily: "warm",
  cardTreatment: "paper",
  compatibleBackgrounds: ["none"],
  theme,
};
