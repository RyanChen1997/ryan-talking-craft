import {z} from 'zod';
import {DEFAULT_PALETTE_ID, PALETTE_IDS} from '../../../assets/visual-kit/palettes';

export const settings = z.object({
  background: z.enum(['checker', 'light', 'dark', 'transparent', 'grid']),
  palette: z.enum(PALETTE_IDS),
  captionBackgroundOpacity: z.number().min(0).max(1),
});

export type PreviewSettings = z.infer<typeof settings>;

export const defaults: PreviewSettings = {
  background: 'grid',
  palette: DEFAULT_PALETTE_ID,
  captionBackgroundOpacity: 0.18,
};
