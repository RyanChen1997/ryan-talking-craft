/**
 * era-photo-compare · 年代照片前后对比
 *
 * 动效本体摘取自参考片 https://www.youtube.com/shorts/kYpdBPpvym0 的 1.4–3.6s 段：
 * 层叠双卡错峰入场 + 描边 ghost 大字被卡片下缘裁切。
 * 调色板与演示文案由调用方注入，本文件只管动效。
 */
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {colorWithAlpha, themeRoles, type MotionTheme} from '../../../../tokens';

export const meta = {width: 960, height: 540, fps: 30, durationInFrames: 99}; // 3.3s（含 0.4s 收尾）

const FPS = meta.fps;

// ——————————————————————————————————————————————————————————
// 可摘走的核心参数
// 命门：① before 卡在下层、after 卡在上层且更大，两卡必须真重叠（并排就变表格，不读作"同一件事的两个阶段"）；
//      ② 两侧角标是完全同款同节奏的静态标签，各自跟着本卡入场——角标是标签不是动效载体，
//         两边做成不同款式会读成"新状态被标记了"，而不是"同一件事的两个阶段"；
//      ③ ghost 大字必须被卡片下缘裁掉约 1/3，完整显示就变成副标题，不再有"海报压边"的层感。
// ——————————————————————————————————————————————————————————
const CONFIG = {
  beforeInAt: 0.20,   // before 卡入场起点 s
  cardIn: 0.42,       // 单卡入场时长 s
  cardGap: 0.14,      // after 卡错峰 s（两卡不同时落定，否则读作一整块）
  rise: 18,           // 入场从下方升起的 px
  slide: 26,          // after 卡入场的水平位移 px（从右侧压上来）
  scaleFrom: 0.98,    // 入场起始缩放（0.94 以下读作弹窗）
  chipLag: 0.42,      // 角标相对本卡入场起点滞后 s（两侧同值）
  chipIn: 0.22,       // 角标淡入 s
  ghostLag: 0.52,     // ghost 大字相对本卡滞后 s
  ghostIn: 0.50,      // ghost 大字升起 s
  ghostRise: 30,      // ghost 大字升起位移 px
  holdEnd: 2.90,      // 静置阅读结束 s
  exitDur: 0.40,      // 退场 s
  end: 3.30,          // 镜头结束 s
};

/* 时间表（demo 秒）
   0.20–0.62  before 卡入场：opacity 0→1、y +18→0、scale 0.98→1（power3.out）
   0.34–0.76  after  卡入场：同上 + x +26→0（power3.out，层级在上，压住 before 卡右缘）
   0.62–0.84  before 角标淡入
   0.76–0.98  after  角标淡入（与本卡同节奏，与 before 完全同款）
   0.72–1.22  before ghost 大字从 +30px 升到位并被卡片下缘裁切
   0.86–1.36  after  ghost 大字同上
   1.36–2.90  静置阅读 1.54s
   2.90–3.30  两卡同收：y -6、opacity→0（power2.in） */

// —— 缓动与 tween helper（对照 GSAP 名字）——
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const tw = (t: number, t0: number, d: number, ease: (x: number) => number) => ease(clamp01((t - t0) / d));
const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
const power2Out = (x: number) => 1 - Math.pow(1 - x, 3);
const power2In = (x: number) => x * x * x;
const power3Out = (x: number) => 1 - Math.pow(1 - x, 4);
/** 颜色插值（#rrggbb → #rrggbb）；无法解析时按 0.5 取端值 */
const mix = (a: string, b: string, p: number) => {
  const pa = a.replace('#', '').match(/\w\w/g);
  const pb = b.replace('#', '').match(/\w\w/g);
  if (!pa || !pb || pa.length < 3 || pb.length < 3) return p < 0.5 ? a : b;
  const to = (h: string) => Number.parseInt(h, 16);
  return `rgb(${pa.map((v, i) => Math.round(lerp(to(v), to(pb[i]), p))).join(',')})`;
};

type CardGeo = {x: number; y: number; w: number; h: number; r: number};

const GEO: Record<'before' | 'after', CardGeo> = {
  before: {x: 44, y: 104, w: 500, h: 340, r: 26},
  after: {x: 372, y: 58, w: 544, h: 424, r: 30},
};

/** before 卡被 after 卡压住的宽度 */
const OVERLAP = GEO.before.x + GEO.before.w - GEO.after.x;
/** before 卡的 ghost 大字按可见区重新居中（左移重叠量的一半） */
const BEFORE_GHOST_SHIFT = -OVERLAP / 2;

export type EraSide = {
  /** 角标文字：年份或短标签 */
  label: string;
  /** 卡片下缘的描边大字（主题 / 名称），会被卡片裁切 */
  caption?: string;
  /** 媒体槽：图片、视频或任意节点；不传用占位底 */
  media?: React.ReactNode;
};

export type EraPhotoCompareProps = {
  theme: MotionTheme;
  before: EraSide;
  after: EraSide;
};

const MediaPlaceholder: React.FC<{theme: MotionTheme}> = ({theme}) => (
  <div
    style={{
      width: '100%',
      height: '100%',
      backgroundImage: `linear-gradient(150deg, ${colorWithAlpha(theme.text, 0.1)}, ${colorWithAlpha(
        theme.text,
        0.03,
      )} 55%, ${colorWithAlpha(theme.primary, 0.16)})`,
    }}
  />
);

type CardProps = {
  theme: MotionTheme;
  geo: CardGeo;
  z: number;
  enter: number;
  slideFrom: number;
  exit: number;
  /** 新状态的那张卡用强调色描边；角标两侧永远同款 */
  emphasized: boolean;
  chip: string;
  chipP: number;
  ghostP: number;
  ghostText?: string;
  ghostSize: number;
  /** ghost 大字水平偏移：被上层卡片遮住的部分不计入排版，按可见区重新居中 */
  ghostShiftX?: number;
  media?: React.ReactNode;
};

const Card: React.FC<CardProps> = ({
  theme,
  geo,
  z,
  enter,
  slideFrom,
  exit,
  emphasized,
  chip,
  chipP,
  ghostP,
  ghostText,
  ghostSize,
  ghostShiftX = 0,
  media,
}) => {
  const roles = themeRoles(theme);
  const inset = geo.w > 520 ? 16 : 14;
  const scale = lerp(CONFIG.scaleFrom, 1, enter);
  const y = lerp(CONFIG.rise, 0, enter) - 6 * exit;
  const x = lerp(slideFrom, 0, enter);
  return (
    <div
      style={{
        position: 'absolute',
        left: geo.x,
        top: geo.y,
        width: geo.w,
        height: geo.h,
        borderRadius: geo.r,
        zIndex: z,
        backgroundColor: theme.surface,
        border: `1.5px solid ${emphasized ? mix(theme.line, theme.primary, 0.6) : theme.line}`,
        boxShadow: roles.cardShadow,
        overflow: 'hidden',
        opacity: enter * (1 - exit),
        transform: `translate(${x}px, ${y}px) scale(${scale})`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: inset,
          top: inset,
          right: inset,
          bottom: inset,
          borderRadius: geo.r - 10,
          overflow: 'hidden',
          backgroundColor: colorWithAlpha(theme.text, 0.04),
        }}
      >
        {media ?? <MediaPlaceholder theme={theme}/>}
      </div>
      <div
        style={{
          position: 'absolute',
          left: inset + 6,
          top: inset + 6,
          opacity: chipP,
          transform: `translateY(${lerp(-6, 0, chipP)}px)`,
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '9px 18px',
            borderRadius: 999,
            backgroundColor: colorWithAlpha(theme.surface, 0.92),
            border: `1.5px solid ${theme.line}`,
            color: roles.onSurface,
            fontFamily: theme.fontFamily,
            fontSize: 22,
            fontWeight: 800,
            letterSpacing: 0.6,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {chip}
        </div>
      </div>
      {ghostText ? (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: -ghostSize * 0.34,
            textAlign: 'center',
            whiteSpace: 'nowrap',
            color: 'transparent',
            WebkitTextStroke: `2px ${colorWithAlpha(roles.onSurface, 0.4)}`,
            fontFamily: theme.fontFamily,
            fontSize: ghostSize,
            fontWeight: 900,
            letterSpacing: 2,
            opacity: ghostP,
            transform: `translate(${ghostShiftX}px, ${lerp(CONFIG.ghostRise, 0, ghostP)}px)`,
          }}
        >
          {ghostText}
        </div>
      ) : null}
    </div>
  );
};

export const EraPhotoCompare: React.FC<EraPhotoCompareProps> = ({theme, before, after}) => {
  const t = useCurrentFrame() / FPS;
  const exit = tw(t, CONFIG.holdEnd, CONFIG.exitDur, power2In);

  const beforeAt = CONFIG.beforeInAt;
  const afterAt = CONFIG.beforeInAt + CONFIG.cardGap;

  const cards = [
    {
      side: before,
      geo: GEO.before,
      at: beforeAt,
      z: 1,
      slideFrom: 0,
      emphasized: false,
      ghostShiftX: BEFORE_GHOST_SHIFT,
      ghostSize: 84,
    },
    {
      side: after,
      geo: GEO.after,
      at: afterAt,
      z: 2,
      slideFrom: CONFIG.slide,
      emphasized: true,
      ghostShiftX: 0,
      ghostSize: 96,
    },
  ] as const;

  return (
    <AbsoluteFill style={{fontFamily: theme.fontFamily, color: theme.text}}>
      {cards.map((card) => (
        <Card
          key={card.geo.x}
          theme={theme}
          geo={card.geo}
          z={card.z}
          enter={tw(t, card.at, CONFIG.cardIn, power3Out)}
          slideFrom={card.slideFrom}
          exit={exit}
          emphasized={card.emphasized}
          chip={card.side.label}
          chipP={tw(t, card.at + CONFIG.chipLag, CONFIG.chipIn, power2Out)}
          ghostP={tw(t, card.at + CONFIG.ghostLag, CONFIG.ghostIn, power3Out)}
          ghostText={card.side.caption}
          ghostSize={card.ghostSize}
          ghostShiftX={card.ghostShiftX}
          media={card.side.media}
        />
      ))}
    </AbsoluteFill>
  );
};

export const Template = EraPhotoCompare;
export default EraPhotoCompare;
