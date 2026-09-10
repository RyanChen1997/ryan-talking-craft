export type Rect = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type StageVariant =
  | 'whiteboard-pip-right'
  | 'whiteboard-pip-left'
  | 'screen-full'
  | 'screen-pip-right'
  | 'screen-pip-left';

export type StageLayoutRects = {
  variant: StageVariant;
  content: Rect;
  safe: Rect;
  pip: Rect | null;
  pipRadius: number;
};

const PIP_WIDTH = 0.172;
const PIP_ASPECT = 4 / 5;
const PIP_EDGE = 0.038;
const PIP_OVERLAP = 0.5;
const FRAME = 0.062;
const PIP_RADIUS = 0.175;
const SAFE_GAP = 0.018;

const roundRect = (rect: Rect): Rect => ({
  x: Math.round(rect.x),
  y: Math.round(rect.y),
  width: Math.round(rect.width),
  height: Math.round(rect.height),
});

export const pipSideOf = (variant: StageVariant): 'left' | 'right' | null => {
  if (variant.endsWith('pip-left')) {
    return 'left';
  }
  if (variant.endsWith('pip-right')) {
    return 'right';
  }
  return null;
};

export const computePipRect = (width: number, height: number, side: 'left' | 'right'): Rect => {
  const pipWidth = width * PIP_WIDTH;
  const pipHeight = pipWidth / PIP_ASPECT;
  const gap = width * PIP_EDGE;
  return roundRect({
    x: side === 'right' ? width - gap - pipWidth : gap,
    y: (height - pipHeight) / 2,
    width: pipWidth,
    height: pipHeight,
  });
};

const fitScreenSlot = (width: number, height: number, pip: Rect | null, side: 'left' | 'right' | null): Rect => {
  const padX = width * FRAME;
  const padY = height * FRAME;
  const maxH = height - padY * 2;
  const maxTop = padY;
  const maxBottom = height - padY;

  let maxLeft = padX;
  let maxRight = width - padX;
  if (pip && side === 'right') {
    maxRight = pip.x + pip.width * PIP_OVERLAP;
  } else if (pip && side === 'left') {
    maxLeft = pip.x + pip.width * (1 - PIP_OVERLAP);
  }

  const maxW = Math.max(1, maxRight - maxLeft);
  let slotW = maxW;
  let slotH = slotW * 9 / 16;
  if (slotH > maxH) {
    slotH = maxH;
    slotW = slotH * 16 / 9;
  }

  const y = Math.max(maxTop, Math.min(maxBottom - slotH, (height - slotH) / 2));
  const x = side === 'left' && pip ? maxLeft : side === 'right' && pip ? maxRight - slotW : padX;

  return roundRect({x, y, width: slotW, height: slotH});
};

const boardSafeRect = (width: number, height: number, pip: Rect | null, side: 'left' | 'right' | null): Rect => {
  if (!pip || !side) {
    return roundRect({x: 0, y: 0, width, height});
  }
  const gap = width * SAFE_GAP;
  if (side === 'right') {
    return roundRect({x: 0, y: 0, width: Math.max(1, pip.x - gap), height});
  }
  const x = pip.x + pip.width + gap;
  return roundRect({x, y: 0, width: Math.max(1, width - x), height});
};

export const computeStageLayout = (width: number, height: number, variant: StageVariant): StageLayoutRects => {
  const side = pipSideOf(variant);
  const pip = side ? computePipRect(width, height, side) : null;
  const whiteboard = variant.startsWith('whiteboard');
  const content = whiteboard
    ? roundRect({x: 0, y: 0, width, height})
    : fitScreenSlot(width, height, pip, side);

  return {
    variant,
    content,
    safe: whiteboard ? boardSafeRect(width, height, pip, side) : content,
    pip,
    pipRadius: pip ? Math.round(pip.width * PIP_RADIUS) : 0,
  };
};

export const STAGE_LAYOUT_IDS = [
  'whiteboard-pip-right@1',
  'whiteboard-pip-left@1',
  'screen-full@1',
  'screen-pip-right@1',
  'screen-pip-left@1',
] as const;

export type StageLayoutId = (typeof STAGE_LAYOUT_IDS)[number];

export const variantFromLayoutId = (id: StageLayoutId): StageVariant =>
  id.replace(/@1$/, '') as StageVariant;
