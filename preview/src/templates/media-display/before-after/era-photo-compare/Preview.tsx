import {createFullscreenPreview} from '../../../../shared/createFullscreenPreview';
import {EraPhotoCompare} from '../../../../../../assets/visual-kit/templates/media-display/before-after/era-photo-compare/Template';

/** 演示语境（不属于动效本体）：两侧角标是同款静态标签，媒体槽留空走占位底。 */
const DEMO = {
  before: {label: '2019', caption: '手动整理'},
  after: {label: '2025', caption: '自动归档'},
};

export const Preview = createFullscreenPreview(({theme}) => (
  <EraPhotoCompare theme={theme} before={DEMO.before} after={DEMO.after}/>
));
