import React from 'react';
import {resolvePalette} from '../../../../../../assets/visual-kit/palettes';
import {StepFlowHorizontal} from '../../../../../../assets/visual-kit/templates/typography/kinetic-type/step-flow-horizontal/Template';
import {createTemplatePreview} from '../../../../shared/createTemplatePreview';

const theme = resolvePalette('grid-hud-cyan@1').theme;
const Motion: React.FC = () => <StepFlowHorizontal theme={theme} />;

export const Preview = createTemplatePreview(Motion, {stage: 'dark'});
