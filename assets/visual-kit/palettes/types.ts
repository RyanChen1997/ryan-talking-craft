import type {MotionTheme} from "../tokens";

export type PaletteStage = "dark" | "light";
export type AccentFamily = "cool" | "warm" | "neutral";
export type CardTreatment = "glass" | "paper";

export type Palette = {
  id: string;
  stage: PaletteStage;
  accentFamily: AccentFamily;
  cardTreatment: CardTreatment;
  compatibleBackgrounds: string[];
  theme: MotionTheme;
};
