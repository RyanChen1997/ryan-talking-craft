import React from 'react';
import {AbsoluteFill, Composition, Folder} from 'remotion';
import {z} from 'zod';
import {DEFAULT_PALETTE_ID, PALETTE_IDS, resolvePalette} from '../../assets/visual-kit/palettes';
import {PerspectiveGridBackground} from '../../assets/visual-kit/background/perspective-grid/Background';
import {CaptionOverlay} from '../../assets/visual-kit/runtime/CaptionOverlay';
import {themeRoles} from '../../assets/visual-kit/tokens';
import {TemplateRegistry} from './templates/registry';
import {
  WhiteboardPipRight,
  WhiteboardPipLeft,
  ScreenFull,
  ScreenPipRight,
  ScreenPipLeft,
} from './layouts/stage/Preview';
import {Preview as CombinationPreview} from './combinations/whiteboard-pip-with-template/Preview';
import {Backdrop} from './shared/Backdrop';

const captionFixture = `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify([
  {text: '字幕提炼之外，口播仍然完整呈现', startMs: 0, endMs: 5000},
  {text: '轻透明底色，让画面更干净', startMs: 5000, endMs: 10000},
]))}`;

const BackgroundPreview: React.FC = () => <PerspectiveGridBackground/>;

const BackgroundCaptions: React.FC<{captionBackgroundOpacity: number; palette: (typeof PALETTE_IDS)[number]}> = ({captionBackgroundOpacity, palette}) => {
  const theme = resolvePalette(palette).theme;
  return (
    <AbsoluteFill style={{backgroundColor: theme.background}}>
      <PerspectiveGridBackground/>
      <CaptionOverlay src={captionFixture} backgroundOpacity={captionBackgroundOpacity} theme={theme}/>
    </AbsoluteFill>
  );
};

const PaletteCompare: React.FC<{palette: (typeof PALETTE_IDS)[number]}> = ({palette}) => {
  const selected = resolvePalette(palette);
  const theme = selected.theme;
  const roles = themeRoles(theme);
  const background = selected.stage === 'dark' ? 'grid' : 'light';
  const swatches = [
    {label: 'primary', color: theme.primary},
    {label: 'secondary', color: theme.secondary},
    {label: 'success', color: theme.success},
    {label: 'warning', color: theme.warning},
  ];
  return (
    <Backdrop kind={background} canvas={theme.background}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', fontFamily: theme.fontFamily}}>
        <div style={{
          minWidth: 520,
          padding: '36px 40px',
          borderRadius: 24,
          background: theme.surface,
          color: roles.onSurface,
          boxShadow: roles.cardShadow,
          border: `1px solid ${theme.line}`,
        }}>
          <div style={{fontSize: 36, fontWeight: 700}}>{selected.id}</div>
          <div style={{marginTop: 8, fontSize: 18, color: roles.mutedOnSurface}}>
            {selected.stage} · {selected.accentFamily} · {selected.cardTreatment}
          </div>
          <div style={{display: 'flex', gap: 14, marginTop: 28}}>
            {swatches.map((item) => (
              <div key={item.label} style={{flex: 1, minWidth: 0}}>
                <div style={{height: 48, borderRadius: 12, background: item.color}}/>
                <div style={{marginTop: 8, fontSize: 14, color: roles.mutedOnSurface}}>{item.label}</div>
              </div>
            ))}
          </div>
        </div>
      </AbsoluteFill>
    </Backdrop>
  );
};

export const RemotionRoot: React.FC = () => <>
  <Folder name="Backgrounds">
    <Composition id="Background-Grid" component={BackgroundPreview} width={1280} height={720} fps={30} durationInFrames={300}/>
    <Composition id="Background-Captions" component={BackgroundCaptions} schema={z.object({captionBackgroundOpacity: z.number().min(0).max(1), palette: z.enum(PALETTE_IDS)})} defaultProps={{captionBackgroundOpacity: 0.18, palette: DEFAULT_PALETTE_ID}} width={1280} height={720} fps={30} durationInFrames={300}/>
  </Folder>
  <Folder name="Palettes">
    <Composition id="Palette-Compare" component={PaletteCompare} schema={z.object({palette: z.enum(PALETTE_IDS)})} defaultProps={{palette: DEFAULT_PALETTE_ID}} width={1280} height={720} fps={30} durationInFrames={180}/>
  </Folder>
  <TemplateRegistry/>
  <Folder name="Layouts">
    <Folder name="Whiteboard">
      <Composition id="Layouts-Whiteboard-PipRight" component={WhiteboardPipRight} width={1280} height={720} fps={30} durationInFrames={120}/>
      <Composition id="Layouts-Whiteboard-PipLeft" component={WhiteboardPipLeft} width={1280} height={720} fps={30} durationInFrames={120}/>
    </Folder>
    <Folder name="Screen">
      <Composition id="Layouts-Screen-Full" component={ScreenFull} width={1280} height={720} fps={30} durationInFrames={120}/>
      <Composition id="Layouts-Screen-PipRight" component={ScreenPipRight} width={1280} height={720} fps={30} durationInFrames={120}/>
      <Composition id="Layouts-Screen-PipLeft" component={ScreenPipLeft} width={1280} height={720} fps={30} durationInFrames={120}/>
    </Folder>
  </Folder>
  <Folder name="Combinations">
    <Composition id="Combinations-Whiteboard-PipRight-NumberedStepStack" component={CombinationPreview} width={1280} height={720} fps={30} durationInFrames={180}/>
  </Folder>
</>;
