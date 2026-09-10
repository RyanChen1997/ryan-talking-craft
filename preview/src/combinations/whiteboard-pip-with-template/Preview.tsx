import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {Template as StepStack} from '../../../../assets/visual-kit/templates/diagram/data-chart/numbered-step-stack/Template';
import {computeStageLayout, StageLayout} from '../../../../assets/visual-kit/layouts/stage/Layout';

const DESIGN_W = 960;
const DESIGN_H = 540;
const PIP = '#7EDCC4';
const INK = '#111111';

const PresenterPlaceholder: React.FC = () => (
  <div
    style={{
      width: '100%',
      height: '100%',
      backgroundColor: PIP,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'Inter, "SF Pro Display", "PingFang SC", sans-serif',
      color: INK,
      fontWeight: 600,
      fontSize: 22,
    }}
  >
    <svg width="46%" height="52%" viewBox="0 0 100 150">
      <circle cx="50" cy="35" r="25" fill="#1d3a34" opacity={0.28} />
      <path d="M8 148V108Q8 72 50 72Q92 72 92 108V148" fill="#1d3a34" opacity={0.28} />
    </svg>
    <span>pip</span>
  </div>
);

export const Preview: React.FC<{pip?: 'left' | 'right'}> = ({pip = 'right'}) => {
  const {width, height} = useVideoConfig();
  const variant = pip === 'left' ? 'whiteboard-pip-left' : 'whiteboard-pip-right';
  const layout = computeStageLayout(width, height, variant);
  const scale = Math.min(layout.safe.width / DESIGN_W, layout.safe.height / DESIGN_H);

  return (
    <AbsoluteFill style={{backgroundColor: '#6EB8EA'}}>
      <StageLayout variant={variant} presenter={<PresenterPlaceholder />}>
        <div
          style={{
            position: 'absolute',
            left: layout.safe.x - layout.content.x,
            top: layout.safe.y - layout.content.y,
            width: layout.safe.width,
            height: layout.safe.height,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              position: 'relative',
              width: DESIGN_W,
              height: DESIGN_H,
              overflow: 'hidden',
              transform: `scale(${scale})`,
              transformOrigin: 'center center',
            }}
          >
            <StepStack />
          </div>
        </div>
      </StageLayout>
    </AbsoluteFill>
  );
};
