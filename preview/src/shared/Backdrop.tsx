import React from 'react';
import {AbsoluteFill} from 'remotion';
import {PerspectiveGridBackground} from '../../../assets/visual-kit/background/perspective-grid/Background';
import type {PreviewSettings} from './previewSettings';

export const Backdrop: React.FC<{
  kind: PreviewSettings['background'];
  canvas?: string;
  children: React.ReactNode;
}> = ({kind, canvas, children}) => (
  <AbsoluteFill style={{
    backgroundColor: kind === 'transparent' ? 'transparent' : kind === 'dark' || kind === 'grid' ? (canvas ?? '#08080A') : '#f4f3f0',
    backgroundImage: kind === 'checker' ? 'conic-gradient(#dededb 25%, transparent 0 50%, #dededb 0 75%, transparent 0)' : undefined,
    backgroundSize: '32px 32px',
  }}>
    {kind === 'grid' ? <PerspectiveGridBackground/> : null}
    {children}
  </AbsoluteFill>
);
