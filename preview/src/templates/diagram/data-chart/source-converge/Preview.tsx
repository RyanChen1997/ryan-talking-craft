import React from 'react';
import {resolvePalette} from '../../../../../../assets/visual-kit/palettes';
import {SourceConverge} from '../../../../../../assets/visual-kit/templates/diagram/data-chart/source-converge/Template';
import {createTemplatePreview} from '../../../../shared/createTemplatePreview';

const theme = resolvePalette('grid-hud-cyan@1').theme;
const Motion: React.FC = () => <SourceConverge theme={theme} />;

export const Preview = createTemplatePreview(Motion, {stage: 'dark'});
