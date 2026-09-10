import React from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {colorWithAlpha, themeRoles, type MotionTheme} from '../../../../tokens';

export const meta = {width: 960, height: 540, fps: 30, durationInFrames: 150};

type Point = {x: number; y: number};

export type SourceConvergeProps = {
  theme: MotionTheme;
  title?: string;
  sources?: string[];
  hub?: string;
  caption?: string;
};

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const sourceX = 170;
const hubStart: Point = {x: 742, y: 282};

const cubicPoint = (start: Point, end: Point, progress: number): Point => {
  const inverse = 1 - progress;
  const controlA = {x: 350, y: start.y};
  const controlB = {x: 540, y: end.y};
  return {
    x: inverse ** 3 * start.x + 3 * inverse ** 2 * progress * controlA.x + 3 * inverse * progress ** 2 * controlB.x + progress ** 3 * end.x,
    y: inverse ** 3 * start.y + 3 * inverse ** 2 * progress * controlA.y + 3 * inverse * progress ** 2 * controlB.y + progress ** 3 * end.y,
  };
};

const pathFor = (start: Point): string =>
  `M ${start.x} ${start.y} C 350 ${start.y}, 540 ${hubStart.y}, ${hubStart.x} ${hubStart.y}`;

export const SourceConverge: React.FC<SourceConvergeProps> = ({
  theme,
  title = '多份信息，汇成一个结论',
  sources = ['封面', '标题', '数据'],
  hub = '5 个发现',
  caption = 'AI 归纳共同规律',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const roles = themeRoles(theme);
  const sourceYs = sources.map((_, index) => 182 + index * 100);
  const merge = interpolate(frame, [48, 91], [0, 1], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  const erase = interpolate(frame, [94, 110], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const center = interpolate(frame, [104, 124], [0, 1], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  const hubX = interpolate(center, [0, 1], [hubStart.x, 480]);
  const hubScale = spring({frame: frame - 23, fps, config: {damping: 12, stiffness: 150}});
  const pulse = spring({frame: frame - 88, fps, config: {damping: 7, stiffness: 190}});
  const titleIn = spring({frame: frame - 3, fps, config: {damping: 14, stiffness: 140}});
  const captionIn = interpolate(frame, [111, 124], [0, 1], clamp);

  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', color: theme.text, fontFamily: theme.fontFamily}}>
      <div
        style={{
          position: 'absolute',
          left: 70,
          top: 55,
          fontSize: 32,
          fontWeight: 760,
          letterSpacing: -0.8,
          opacity: titleIn,
          transform: `translateY(${(1 - titleIn) * 12}px)`,
        }}
      >
        {title}
      </div>

      <svg width="960" height="540" viewBox="0 0 960 540" style={{position: 'absolute', inset: 0}}>
        {sourceYs.map((y, index) => {
          const start = {x: sourceX, y};
          const draw = interpolate(frame, [16 + index * 5, 38 + index * 5], [0, 1], {
            ...clamp,
            easing: Easing.out(Easing.cubic),
          });
          const packetProgress = ((Math.max(0, frame - 29) / 45) + index * 0.17) % 1;
          const packet = cubicPoint(start, hubStart, packetProgress);
          const packetOpacity = interpolate(frame, [28, 38, 82, 94], [0, 1, 1, 0], clamp);
          return (
            <React.Fragment key={sources[index]}>
              <path
                d={pathFor(start)}
                pathLength={1}
                fill="none"
                stroke={colorWithAlpha(theme.primary, 0.48)}
                strokeWidth={2.2}
                strokeDasharray={1}
                strokeDashoffset={(1 - draw) + erase}
              />
              <circle cx={packet.x} cy={packet.y} r={5} fill={theme.secondary} opacity={packetOpacity * (1 - erase)} />
            </React.Fragment>
          );
        })}
      </svg>

      {sourceYs.map((y, index) => {
        const start = {x: sourceX, y};
        const position = cubicPoint(start, hubStart, merge);
        const enter = spring({frame: frame - 8 - index * 4, fps, config: {damping: 13, stiffness: 165}});
        const shrink = interpolate(merge, [0, 0.72, 1], [1, 0.78, 0], clamp);
        return (
          <div
            key={sources[index]}
            style={{
              position: 'absolute',
              left: position.x,
              top: position.y,
              minWidth: 128,
              padding: '12px 20px',
              borderRadius: 999,
              background: colorWithAlpha(theme.surface, 0.94),
              border: `1px solid ${colorWithAlpha(theme.primary, 0.45)}`,
              boxShadow: roles.cardShadow,
              color: roles.onSurface,
              fontSize: 21,
              fontWeight: 650,
              textAlign: 'center',
              opacity: enter * (1 - interpolate(merge, [0.82, 1], [0, 1], clamp)),
              transform: `translate(-50%, -50%) scale(${enter * shrink})`,
            }}
          >
            {sources[index]}
          </div>
        );
      })}

      <div
        style={{
          position: 'absolute',
          left: hubX,
          top: hubStart.y,
          minWidth: 174,
          padding: '17px 26px',
          borderRadius: 999,
          background: theme.primary,
          color: roles.onAccent,
          fontSize: 25,
          fontWeight: 780,
          textAlign: 'center',
          boxShadow: `0 0 0 1px ${colorWithAlpha(theme.primary, 0.65)}, 0 16px 40px ${colorWithAlpha(theme.primary, 0.24)}`,
          opacity: hubScale,
          transform: `translate(-50%, -50%) scale(${hubScale * (1 + pulse * 0.07)})`,
        }}
      >
        {hub}
      </div>

      <div
        style={{
          position: 'absolute',
          left: hubX,
          top: 355,
          color: theme.mutedText,
          fontSize: 21,
          fontWeight: 600,
          opacity: captionIn,
          transform: `translate(-50%, ${(1 - captionIn) * 8}px)`,
        }}
      >
        {caption}
      </div>
    </div>
  );
};

export default SourceConverge;
export const Template = SourceConverge;
