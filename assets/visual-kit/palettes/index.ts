import {palette as gridCinemaAmber} from "./grid-cinema-amber/palette";
import {palette as gridHudCyan} from "./grid-hud-cyan/palette";
import {palette as gridNeutralGold} from "./grid-neutral-gold/palette";
import {palette as paperDay} from "./paper-day/palette";
import type {Palette} from "./types";

export type {AccentFamily, CardTreatment, Palette, PaletteStage} from "./types";

export const PALETTE_IDS = [
  "grid-hud-cyan@1",
  "grid-cinema-amber@1",
  "grid-neutral-gold@1",
  "paper-day@1",
] as const;

export type PaletteId = (typeof PALETTE_IDS)[number];

export const DEFAULT_PALETTE_ID: PaletteId = "grid-hud-cyan@1";

export const palettes: Record<PaletteId, Palette> = {
  "grid-hud-cyan@1": gridHudCyan,
  "grid-cinema-amber@1": gridCinemaAmber,
  "grid-neutral-gold@1": gridNeutralGold,
  "paper-day@1": paperDay,
};

export function resolvePalette(id: string): Palette {
  const palette = palettes[id as PaletteId];
  if (!palette) {
    throw new Error(`Unknown palette: ${id}`);
  }
  return palette;
}

export const defaultTheme = gridHudCyan.theme;
export const gridStageTheme = gridHudCyan.theme;
