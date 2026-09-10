import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';

/** VTC staging templates are authored for 960×540 design coordinates. */
const DESIGN_W = 960;
const DESIGN_H = 540;

export type TemplatePreviewStage = 'light' | 'dark';

export type TemplatePreviewOptions = {
  /** Most VTC typography/diagram demos assume a light paper stage. */
  stage?: TemplatePreviewStage;
};

/**
 * Wraps a motion-only Template for Remotion Studio.
 * Does NOT inject StageLayout or the perspective grid —
 * those live under Layouts / Backgrounds / Combinations.
 */
export const createTemplatePreview = (
  Motion: React.ComponentType,
  options: TemplatePreviewOptions = {},
): React.FC => {
  const stage = options.stage ?? 'light';

  const Preview: React.FC = () => {
    const {width, height} = useVideoConfig();
    const scale = Math.min(width / DESIGN_W, height / DESIGN_H);
    const paper = stage === 'light' ? '#f4f3f0' : '#08080A';
    const canvas = stage === 'light' ? '#ffffff' : '#111113';

    return (
      <AbsoluteFill
        style={{
          backgroundColor: paper,
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <div
          style={{
            position: 'relative',
            width: DESIGN_W,
            height: DESIGN_H,
            backgroundColor: canvas,
            overflow: 'hidden',
            transform: `scale(${scale})`,
            transformOrigin: 'center center',
            isolation: 'isolate',
          }}
        >
          <Motion/>
        </div>
      </AbsoluteFill>
    );
  };

  Preview.displayName = `TemplatePreview(${Motion.displayName ?? Motion.name ?? 'Motion'})`;
  return Preview;
};
