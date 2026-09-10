import React from 'react';
import {AbsoluteFill} from 'remotion';
import {StageLayout, type StageVariant} from '../../../../assets/visual-kit/layouts/stage/Layout';

const BOARD = '#6EB8EA';
const PIP = '#7EDCC4';
const SCREEN = '#F0D056';
const INK = '#111111';
const FONT = 'Inter, "SF Pro Display", "PingFang SC", sans-serif';

const FillLabel: React.FC<{color: string; label: string}> = ({color, label}) => (
  <div
    style={{
      width: '100%',
      height: '100%',
      backgroundColor: color,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: FONT,
      fontSize: 28,
      fontWeight: 600,
      color: INK,
    }}
  >
    {label}
  </div>
);

export const SchematicPreview: React.FC<{variant: StageVariant}> = ({variant}) => (
  <AbsoluteFill style={{backgroundColor: BOARD}}>
    <StageLayout
      variant={variant}
      presenter={<FillLabel color={PIP} label="pip" />}
    >
      {variant.startsWith('screen') ? <FillLabel color={SCREEN} label="录屏演示" /> : null}
    </StageLayout>
  </AbsoluteFill>
);

export const WhiteboardPipRight: React.FC = () => <SchematicPreview variant="whiteboard-pip-right" />;
export const WhiteboardPipLeft: React.FC = () => <SchematicPreview variant="whiteboard-pip-left" />;
export const ScreenFull: React.FC = () => <SchematicPreview variant="screen-full" />;
export const ScreenPipRight: React.FC = () => <SchematicPreview variant="screen-pip-right" />;
export const ScreenPipLeft: React.FC = () => <SchematicPreview variant="screen-pip-left" />;
