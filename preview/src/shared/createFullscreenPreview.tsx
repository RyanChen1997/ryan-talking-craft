import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {resolvePalette, type PaletteId} from '../../../assets/visual-kit/palettes';
import {PerspectiveGridBackground} from '../../../assets/visual-kit/background/perspective-grid/Background';
import type {MotionTheme} from '../../../assets/visual-kit/tokens';

/** 全屏画面模板按 960×540 设计坐标书写。 */
const DESIGN_W = 960;
const DESIGN_H = 540;

export type FullscreenPreviewProps = {
  /** Studio props 面板里可切换；深色舞台配色自动叠透视网格背景 */
  palette: PaletteId;
};

/**
 * 全屏画面模板的 Studio 预览入口。
 *
 * 与 `createTemplatePreview` 的区别：那个给的是 960×540 的"纸面画框"，适合嵌在舞台里的动效；
 * 这里整幅画布就是模板自己的舞台（背景、卡片、版面都归模板），所以背景直接用 palette 的
 * `theme.background`，不额外加纸面。
 *
 * 一个模板只注册一个 Composition：配色从 props 面板切，不给每套配色另开一条
 * Composition——模板接收的是 `theme` 角色，不是某套固定配色。
 */
export const createFullscreenPreview = (
  render: (context: {theme: MotionTheme}) => React.ReactNode,
): React.FC<FullscreenPreviewProps> => {
  const Preview: React.FC<FullscreenPreviewProps> = ({palette}) => {
    const {width, height} = useVideoConfig();
    const resolved = resolvePalette(palette);
    const theme = resolved.theme;
    const scale = Math.min(width / DESIGN_W, height / DESIGN_H);

    return (
      <AbsoluteFill style={{backgroundColor: theme.background}}>
        {resolved.stage === 'dark' ? (
          <PerspectiveGridBackground canvas={theme.background}/>
        ) : null}
        <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
          <div
            style={{
              position: 'relative',
              width: DESIGN_W,
              height: DESIGN_H,
              transform: `scale(${scale})`,
              transformOrigin: 'center center',
              isolation: 'isolate',
            }}
          >
            {render({theme})}
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  };
  Preview.displayName = 'FullscreenPreview';
  return Preview;
};
