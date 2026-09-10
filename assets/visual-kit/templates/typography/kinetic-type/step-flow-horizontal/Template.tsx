import React from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {colorWithAlpha, themeRoles, type MotionTheme} from '../../../../tokens';

export const meta = {width: 960, height: 540, fps: 30, durationInFrames: 150};

export type StepFlowHorizontalStep = {
  label: string;
  detail: string;
};

export type StepFlowHorizontalProps = {
  theme: MotionTheme;
  title?: string;
  steps?: StepFlowHorizontalStep[];
  conclusion?: string;
};

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const StepFlowHorizontal: React.FC<StepFlowHorizontalProps> = ({
  theme,
  title = '完整闭环，不只介绍功能',
  steps = [
    {label: '原稿', detail: '内容输入'},
    {label: '成稿', detail: '自动排版'},
    {label: '草稿箱', detail: '直接发布'},
  ],
  conclusion = '把整件事做完',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const roles = themeRoles(theme);
  const titleIn = spring({frame: frame - 2, fps, config: {damping: 14, stiffness: 150}});
  const conclusionIn = spring({frame: frame - 86, fps, config: {damping: 10, stiffness: 165}});

  return (
    <div style={{position: 'absolute', inset: 0, color: theme.text, fontFamily: theme.fontFamily}}>
      <div
        style={{
          position: 'absolute',
          left: 64,
          right: 64,
          top: 57,
          textAlign: 'center',
          fontSize: 32,
          fontWeight: 760,
          letterSpacing: -0.8,
          opacity: titleIn,
          transform: `translateY(${(1 - titleIn) * 12}px)`,
        }}
      >
        {title}
      </div>

      <div
        style={{
          position: 'absolute',
          left: 58,
          right: 58,
          top: 176,
          display: 'flex',
          alignItems: 'center',
        }}
      >
        {steps.map((step, index) => {
          const enterAt = 18 + index * 21;
          const bounce = spring({
            frame: frame - enterAt,
            fps,
            config: {damping: 7.5, mass: 0.72, stiffness: 175},
          });
          const isLast = index === steps.length - 1;
          const settleGlow = isLast
            ? interpolate(frame, [enterAt + 17, enterAt + 30], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)})
            : 0;
          const arrowDraw = interpolate(frame, [enterAt + 10, enterAt + 24], [0, 1], {
            ...clamp,
            easing: Easing.out(Easing.cubic),
          });

          return (
            <React.Fragment key={`${step.label}-${index}`}>
              <div
                style={{
                  position: 'relative',
                  zIndex: 1,
                  flex: '1 1 0',
                  minWidth: 0,
                  height: 156,
                  borderRadius: 24,
                  background: colorWithAlpha(theme.surface, 0.94),
                  border: `1px solid ${isLast ? colorWithAlpha(theme.secondary, 0.8) : colorWithAlpha(theme.primary, 0.34)}`,
                  boxShadow: isLast && settleGlow > 0
                    ? `0 0 0 ${settleGlow * 5}px ${colorWithAlpha(theme.secondary, 0.1)}, 0 18px 42px ${colorWithAlpha(theme.secondary, 0.2)}`
                    : roles.cardShadow,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity: Math.min(1, bounce),
                  transform: `translateY(${(1 - bounce) * 42}px) scale(${0.72 + bounce * 0.28})`,
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    left: 14,
                    top: 13,
                    width: 30,
                    height: 30,
                    borderRadius: 10,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: isLast ? theme.secondary : colorWithAlpha(theme.primary, 0.16),
                    color: isLast ? roles.onAccent : theme.primary,
                    fontSize: 15,
                    fontWeight: 800,
                  }}
                >
                  {index + 1}
                </div>
                <div style={{fontSize: 31, fontWeight: 790, letterSpacing: -0.5}}>{step.label}</div>
                <div style={{marginTop: 9, color: theme.mutedText, fontSize: 18, fontWeight: 560}}>{step.detail}</div>
              </div>

              {!isLast ? (
                <div
                  style={{
                    position: 'relative',
                    zIndex: 2,
                    flex: '0 0 72px',
                    height: 52,
                  }}
                >
                  <svg width="72" height="52" viewBox="0 0 72 52" style={{display: 'block', overflow: 'visible'}}>
                    <path
                      d="M 7 26 C 23 15, 43 15, 59 26"
                      pathLength={1}
                      fill="none"
                      stroke={theme.primary}
                      strokeWidth={4}
                      strokeLinecap="round"
                      strokeDasharray={1}
                      strokeDashoffset={1 - arrowDraw}
                    />
                    <path
                      d="M 52 18 L 62 26 L 52 34"
                      pathLength={1}
                      fill="none"
                      stroke={theme.primary}
                      strokeWidth={4}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray={1}
                      strokeDashoffset={1 - arrowDraw}
                    />
                  </svg>
                </div>
              ) : null}
            </React.Fragment>
          );
        })}
      </div>

      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: 407,
          padding: '11px 22px',
          borderRadius: 999,
          background: colorWithAlpha(theme.secondary, 0.13),
          border: `1px solid ${colorWithAlpha(theme.secondary, 0.52)}`,
          color: theme.secondary,
          fontSize: 20,
          fontWeight: 720,
          opacity: conclusionIn,
          transform: `translateX(-50%) scale(${0.8 + conclusionIn * 0.2})`,
        }}
      >
        {conclusion}
      </div>
    </div>
  );
};

export default StepFlowHorizontal;
export const Template = StepFlowHorizontal;
