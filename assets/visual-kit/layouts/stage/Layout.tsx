import React from 'react';
import {useVideoConfig} from 'remotion';
import {computeStageLayout, type StageVariant} from './geometry';

export type {StageLayoutId, StageVariant} from './geometry';
export {computeStageLayout, STAGE_LAYOUT_IDS, variantFromLayoutId} from './geometry';

export type StageLayoutProps = {
  variant: StageVariant;
  presenter?: React.ReactNode;
  children?: React.ReactNode;
};

/** Pure space allocation. Does not own media, narration, animation or source time. */
export const StageLayout: React.FC<StageLayoutProps> = ({variant, presenter, children}) => {
  const {width, height} = useVideoConfig();
  const layout = computeStageLayout(width, height, variant);

  return (
    <div style={{position: 'absolute', inset: 0}}>
      <div
        data-content-region
        data-layout-variant={variant}
        style={{
          position: 'absolute',
          left: layout.content.x,
          top: layout.content.y,
          width: layout.content.width,
          height: layout.content.height,
          overflow: 'hidden',
        }}
      >
        {children}
      </div>
      {layout.pip && presenter ? (
        <div
          data-presenter-region
          style={{
            position: 'absolute',
            left: layout.pip.x,
            top: layout.pip.y,
            width: layout.pip.width,
            height: layout.pip.height,
            overflow: 'hidden',
            borderRadius: layout.pipRadius,
          }}
        >
          {presenter}
        </div>
      ) : null}
    </div>
  );
};
