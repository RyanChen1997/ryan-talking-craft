import {createFullscreenPreview} from '../../../../shared/createFullscreenPreview';
import {CurtainPushCompare} from '../../../../../../assets/visual-kit/templates/typography/before-after/curtain-push-compare/Template';

/** 演示语境（不属于动效本体）。 */
const DEMO = {
  before: {label: '改版前', verdict: '手动整理', detail: '两小时起，还容易漏掉文件'},
  after: {label: '改版后', verdict: '自动归档', detail: '十分钟看完，零遗漏'},
};

export const Preview = createFullscreenPreview(({theme}) => (
  <CurtainPushCompare theme={theme} before={DEMO.before} after={DEMO.after}/>
));
