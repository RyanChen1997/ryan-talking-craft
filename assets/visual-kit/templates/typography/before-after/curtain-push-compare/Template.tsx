/**
 * curtain-push-compare · 中缝裂开式前后对比
 *
 * 动效本体摘取自参考片 https://www.youtube.com/shorts/4sXwOnaRPuQ 的 2.30–2.85s 段：
 * 中央先出现一条亮缝，缝向两侧裂开成两道边；旧状态被这两道边推向左右并被面板裁掉，
 * 新状态从中缝之间长出来；结论词的下划线随后自左向右画出。
 * 调色板与演示文案由调用方注入，本文件只管动效。
 */
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {colorWithAlpha, themeRoles, type MotionTheme} from '../../../../tokens';

export const meta = {width: 960, height: 540, fps: 30, durationInFrames: 144}; // 4.8s（含 0.4s 收尾）

const FPS = meta.fps;

// ——————————————————————————————————————————————————————————
// 可摘走的核心参数
// 命门：① 新状态不是"淡入"进来的，是被中缝的 clip 生长露出来的——加了淡入就变成两个动作；
//      ② 旧状态必须真的被推走并被面板裁掉（在 panel 上 overflow hidden），只在原地变灰读作"变暗"不是"被替换"；
//      ③ 中缝的边线要跟着旧状态一起被推出去，留在原地就成了装饰线；
//      ④ 全卡只有结论词的下划线一个强调动作，结论词本身不动（再弹一下就从"结论落定"变成"按钮点击"）。
// ——————————————————————————————————————————————————————————
const CONFIG = {
  panelInAt: 0.20,    // 面板入场起点 s
  panelIn: 0.42,      // 面板入场 s
  panelRise: 14,      // 入场从下方升起 px
  copyLag: 0.10,      // label / 结论 / 副行 相对面板入场起点的滞后 s
  copyStagger: 0.10,  // 三行错峰 s
  copyIn: 0.30,       // 单行淡入 s
  seamAt: 1.10,       // 中缝出现起点 s
  seamIn: 0.16,       // 中缝长满 s（scaleY 0→1）
  openAt: 1.30,       // 裂开起点 s
  openDur: 0.42,      // 裂开时长 s（power3.inOut；<0.3 读作闪切）
  pushRatio: 1,       // 旧状态被推出的距离 = 面板半宽 × 该系数 × open
  beforeOut: 0.25,    // 旧状态被推到底时剩下的不透明度（归零会让"替换"失去对照）
  underlineAt: 1.96,  // 结论词下划线起点 s
  underlineDur: 0.34, // 下划线生长 s
  glowAt: 2.00,       // 结论词辉光起点 s
  glowDur: 0.40,      // 辉光淡入 s
  popAt: 2.30,        // 结论词落定微缩 s
  popDur: 0.14,
  holdEnd: 4.30,      // 静置阅读结束 s
  exitDur: 0.40,      // 退场 s
  end: 4.80,          // 镜头结束 s
};

/* 时间表（demo 秒）
   0.20–0.62  面板入场：opacity 0→1、y +14→0、scale 0.985→1（power3.out）
   0.30–0.90  label / 结论词 / 副行 错峰淡入（0.30s power2.out，y 8→0）
   1.10–1.26  中缝出现：中央 6px 缝长满（scaleY 0→1，power2.out）
   1.30–1.72  裂开：open 0→1（power3.inOut）
              → 旧状态两半各被推出 面板半宽×1（被面板裁掉），不透明度 1→0.25
              → 两道缝边跟着一起被推出（opacity→0）
              → 新状态由中央 clip 生长露出来（无额外淡入）
   1.96–2.30  结论词下划线自左向右画出（0.34s power2.out）+ 辉光淡入 0.40s
   2.30–2.44  结论词 1.02→1 落定（power2.out）
   2.44–4.30  静置阅读 1.86s
   4.30–4.80  面板同收：y -8、opacity→0（power2.in） */

// —— 缓动与 tween helper（对照 GSAP 名字）——
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const tw = (t: number, t0: number, d: number, ease: (x: number) => number) => ease(clamp01((t - t0) / d));
const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
const power2Out = (x: number) => 1 - Math.pow(1 - x, 3);
const power2In = (x: number) => x * x * x;
const power3Out = (x: number) => 1 - Math.pow(1 - x, 4);
const power3InOut = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);

const PANEL = {x: 190, y: 70, w: 580, h: 400, r: 28};
const PAD = 36;

export type ComparePanelContent = {
  /** 状态标签，如「改版前」 */
  label: string;
  /** 结论词（唯一强调目标） */
  verdict: string;
  /** 副行说明 */
  detail?: string;
};

export type CurtainPushCompareProps = {
  theme: MotionTheme;
  before: ComparePanelContent;
  after: ComparePanelContent;
};

const PanelCopy: React.FC<{
  theme: MotionTheme;
  content: ComparePanelContent;
  /** 每行的入场进度（label / verdict / detail） */
  p: readonly number[];
  /** 强调强度：0 = 未强调（label 空心、无下划线） */
  accent: number;
  underline: number;
  glow: number;
  popScale: number;
  pillSolid: boolean;
}> = ({theme, content, p, accent, underline, glow, popScale, pillSolid}) => {
  const roles = themeRoles(theme);
  return (
    <>
      <div
        style={{
          position: 'absolute',
          left: PAD,
          top: PAD - 4,
          display: 'inline-flex',
          alignItems: 'center',
          padding: '8px 18px',
          borderRadius: 999,
          backgroundColor: pillSolid ? theme.primary : colorWithAlpha(theme.surface, 0.9),
          border: `1.5px solid ${pillSolid ? theme.primary : theme.line}`,
          color: pillSolid ? roles.onAccent : roles.mutedOnSurface,
          fontSize: 20,
          fontWeight: 800,
          letterSpacing: 1,
          opacity: p[0],
          transform: `translateY(${lerp(8, 0, p[0])}px)`,
        }}
      >
        {content.label}
      </div>
      <div
        style={{
          position: 'absolute',
          left: PAD,
          right: PAD,
          top: 152,
          fontSize: 54,
          fontWeight: 800,
          letterSpacing: 1,
          lineHeight: 1.15,
          opacity: p[1],
          transform: `translateY(${lerp(8, 0, p[1])}px) scale(${popScale})`,
          transformOrigin: 'left center',
        }}
      >
        <span
          style={{
            display: 'inline-block',
            paddingBottom: 12,
            // 两层背景：下层是 4px 下划线，跟随 underline 从左向右生长；上层不画，避免盖住字
            backgroundImage: `linear-gradient(${theme.primary}, ${theme.primary})`,
            backgroundRepeat: 'no-repeat',
            backgroundPosition: '0 100%',
            backgroundSize: `${underline * 100}% 4px`,
            textShadow: glow > 0 ? `0 0 26px ${colorWithAlpha(theme.primary, 0.45 * glow)}` : undefined,
          }}
        >
          {content.verdict}
        </span>
      </div>
      {content.detail ? (
        <div
          style={{
            position: 'absolute',
            left: PAD,
            right: PAD,
            top: 262,
            fontSize: 24,
            lineHeight: 1.5,
            color: accent > 0 ? roles.onSurface : roles.mutedOnSurface,
            opacity: p[2] * lerp(0.85, 1, accent),
            transform: `translateY(${lerp(8, 0, p[2])}px)`,
          }}
        >
          {content.detail}
        </div>
      ) : null}
    </>
  );
};

export const CurtainPushCompare: React.FC<CurtainPushCompareProps> = ({theme, before, after}) => {
  const t = useCurrentFrame() / FPS;
  const roles = themeRoles(theme);

  const panelEnter = tw(t, CONFIG.panelInAt, CONFIG.panelIn, power3Out);
  const exit = tw(t, CONFIG.holdEnd, CONFIG.exitDur, power2In);

  const copyP = (index: number) =>
    tw(t, CONFIG.panelInAt + CONFIG.copyLag + index * CONFIG.copyStagger, CONFIG.copyIn, power2Out);

  const seamP = tw(t, CONFIG.seamAt, CONFIG.seamIn, power2Out);
  const open = tw(t, CONFIG.openAt, CONFIG.openDur, power3InOut);
  const push = PANEL.w / 2 * CONFIG.pushRatio * open;
  // 缝边比旧状态多走 12px，才能整体退出面板被裁掉（留在边上会变成一条装饰线）
  const edgePush = (PANEL.w / 2 + 12) * open;

  const underline = tw(t, CONFIG.underlineAt, CONFIG.underlineDur, power2Out);
  const glow = tw(t, CONFIG.glowAt, CONFIG.glowDur, power2Out);
  const pop = tw(t, CONFIG.popAt, CONFIG.popDur, power2Out);

  const panelStyle: React.CSSProperties = {
    position: 'absolute',
    left: PANEL.x,
    top: PANEL.y,
    width: PANEL.w,
    height: PANEL.h,
    borderRadius: PANEL.r,
    backgroundColor: theme.surface,
    border: `1.5px solid ${theme.line}`,
    boxShadow: roles.cardShadow,
    overflow: 'hidden',
    fontFamily: theme.fontFamily,
    color: theme.text,
  };

  return (
    <AbsoluteFill style={{fontFamily: theme.fontFamily, color: theme.text}}>
      <div
        style={{
          ...panelStyle,
          opacity: panelEnter * (1 - exit),
          transform: `translateY(${lerp(CONFIG.panelRise, 0, panelEnter) - 8 * exit}px) scale(${lerp(
            0.985,
            1,
            panelEnter,
          )})`,
        }}
      >
        {/* 新状态：由中央 clip 生长露出，不做淡入 */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            clipPath: `inset(0 ${(1 - open) * 50}% 0 ${(1 - open) * 50}%)`,
          }}
        >
          <PanelCopy
            theme={theme}
            content={after}
            p={[copyP(0), copyP(1), copyP(2)]}
            accent={glow}
            underline={underline}
            glow={glow}
            popScale={lerp(1.02, 1, pop)}
            pillSolid
          />
        </div>

        {/* 旧状态：左右两半被缝推向两侧，最终被面板裁掉 */}
        {([
          {clip: 'inset(0 50% 0 0)', dir: -1, p: copyP(0)},
          {clip: 'inset(0 0 0 50%)', dir: 1, p: copyP(0)},
        ] as const).map((half, index) => (
          <div
            key={index}
            style={{
              position: 'absolute',
              inset: 0,
              clipPath: half.clip,
              transform: `translateX(${half.dir * push}px)`,
              opacity: lerp(1, CONFIG.beforeOut, open),
            }}
          >
            <PanelCopy
              theme={theme}
              content={before}
              p={[copyP(0), copyP(1), copyP(2)]}
              accent={0}
              underline={0}
              glow={0}
              popScale={1}
              pillSolid={false}
            />
          </div>
        ))}

        {/* 中缝：两条边线在中央重合时读作一条 6px 缝，裂开时一起向外走并被面板裁掉 */}
        {([1, -1] as const).map((dir) => (
          <div
            key={dir}
            style={{
              position: 'absolute',
              left: '50%',
              top: 0,
              bottom: 0,
              width: 6,
              marginLeft: -3,
              backgroundColor: theme.primary,
              boxShadow: `0 0 18px ${colorWithAlpha(theme.primary, 0.5)}`,
              transform: `translateX(${dir * edgePush}px) scaleY(${seamP})`,
              transformOrigin: 'center',
              opacity: seamP,
            }}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};

export const Template = CurtainPushCompare;
export default CurtainPushCompare;
