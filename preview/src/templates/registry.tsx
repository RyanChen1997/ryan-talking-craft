import React from 'react';
import {Composition, Folder} from 'remotion';
import {z} from 'zod';
import {DEFAULT_PALETTE_ID, PALETTE_IDS} from '../../../assets/visual-kit/palettes';
import {Preview as Preview_bar_chart_growth} from './diagram/data-chart/bar-chart-growth/Preview';
import {meta as meta_bar_chart_growth} from '../../../assets/visual-kit/templates/diagram/data-chart/bar-chart-growth/Template';
import {Preview as Preview_chart_grow} from './diagram/data-chart/chart-grow/Preview';
import {meta as meta_chart_grow} from '../../../assets/visual-kit/templates/diagram/data-chart/chart-grow/Template';
import {Preview as Preview_chip_grid_single_select} from './diagram/data-chart/chip-grid-single-select/Preview';
import {meta as meta_chip_grid_single_select} from '../../../assets/visual-kit/templates/diagram/data-chart/chip-grid-single-select/Template';
import {Preview as Preview_info_term_card} from './diagram/data-chart/info-term-card/Preview';
import {meta as meta_info_term_card} from '../../../assets/visual-kit/templates/diagram/data-chart/info-term-card/Template';
import {Preview as Preview_line_chart_story_draw} from './diagram/data-chart/line-chart-story-draw/Preview';
import {meta as meta_line_chart_story_draw} from '../../../assets/visual-kit/templates/diagram/data-chart/line-chart-story-draw/Template';
import {Preview as Preview_map_route_pin} from './diagram/data-chart/map-route-pin/Preview';
import {meta as meta_map_route_pin} from '../../../assets/visual-kit/templates/diagram/data-chart/map-route-pin/Template';
import {Preview as Preview_metric_with_sparkline} from './diagram/data-chart/metric-with-sparkline/Preview';
import {meta as meta_metric_with_sparkline} from '../../../assets/visual-kit/templates/diagram/data-chart/metric-with-sparkline/Template';
import {Preview as Preview_number_counter} from './diagram/data-chart/number-counter/Preview';
import {meta as meta_number_counter} from '../../../assets/visual-kit/templates/diagram/data-chart/number-counter/Template';
import {Preview as Preview_number_slab_pop} from './diagram/data-chart/number-slab-pop/Preview';
import {meta as meta_number_slab_pop} from '../../../assets/visual-kit/templates/diagram/data-chart/number-slab-pop/Template';
import {Preview as Preview_numbered_step_stack} from './diagram/data-chart/numbered-step-stack/Preview';
import {meta as meta_numbered_step_stack} from '../../../assets/visual-kit/templates/diagram/data-chart/numbered-step-stack/Template';
import {Preview as Preview_source_converge} from './diagram/data-chart/source-converge/Preview';
import {meta as meta_source_converge} from '../../../assets/visual-kit/templates/diagram/data-chart/source-converge/Template';
import {Preview as Preview_step_timeline_vertical} from './diagram/data-chart/step-timeline-vertical/Preview';
import {meta as meta_step_timeline_vertical} from '../../../assets/visual-kit/templates/diagram/data-chart/step-timeline-vertical/Template';
import {Preview as Preview_ui_prop_theater} from './diagram/data-chart/ui-prop-theater/Preview';
import {meta as meta_ui_prop_theater} from '../../../assets/visual-kit/templates/diagram/data-chart/ui-prop-theater/Template';
import {Preview as Preview_unit_grid_proportion} from './diagram/data-chart/unit-grid-proportion/Preview';
import {meta as meta_unit_grid_proportion} from '../../../assets/visual-kit/templates/diagram/data-chart/unit-grid-proportion/Template';
import {Preview as Preview_converging_arrows} from './typography/emphasis/converging-arrows/Preview';
import {meta as meta_converging_arrows} from '../../../assets/visual-kit/templates/typography/emphasis/converging-arrows/Template';
import {Preview as Preview_corner_bracket_frame} from './typography/emphasis/corner-bracket-frame/Preview';
import {meta as meta_corner_bracket_frame} from '../../../assets/visual-kit/templates/typography/emphasis/corner-bracket-frame/Template';
import {Preview as Preview_hand_drawn_ellipse} from './typography/emphasis/hand-drawn-ellipse/Preview';
import {meta as meta_hand_drawn_ellipse} from '../../../assets/visual-kit/templates/typography/emphasis/hand-drawn-ellipse/Template';
import {Preview as Preview_ink_underline} from './typography/emphasis/ink-underline/Preview';
import {meta as meta_ink_underline} from '../../../assets/visual-kit/templates/typography/emphasis/ink-underline/Template';
import {Preview as Preview_quote_hold_arrow} from './typography/emphasis/quote-hold-arrow/Preview';
import {meta as meta_quote_hold_arrow} from '../../../assets/visual-kit/templates/typography/emphasis/quote-hold-arrow/Template';
import {Preview as Preview_strike_and_replace} from './typography/emphasis/strike-and-replace/Preview';
import {meta as meta_strike_and_replace} from '../../../assets/visual-kit/templates/typography/emphasis/strike-and-replace/Template';
import {Preview as Preview_alt_block_lines} from './typography/kinetic-type/alt-block-lines/Preview';
import {meta as meta_alt_block_lines} from '../../../assets/visual-kit/templates/typography/kinetic-type/alt-block-lines/Template';
import {Preview as Preview_count_badge_title} from './typography/kinetic-type/count-badge-title/Preview';
import {meta as meta_count_badge_title} from '../../../assets/visual-kit/templates/typography/kinetic-type/count-badge-title/Template';
import {Preview as Preview_countdown_arc_scatter} from './typography/kinetic-type/countdown-arc-scatter/Preview';
import {meta as meta_countdown_arc_scatter} from '../../../assets/visual-kit/templates/typography/kinetic-type/countdown-arc-scatter/Template';
import {Preview as Preview_error_retype} from './typography/kinetic-type/error-retype/Preview';
import {meta as meta_error_retype} from '../../../assets/visual-kit/templates/typography/kinetic-type/error-retype/Template';
import {Preview as Preview_flying_words} from './typography/kinetic-type/flying-words/Preview';
import {meta as meta_flying_words} from '../../../assets/visual-kit/templates/typography/kinetic-type/flying-words/Template';
import {Preview as Preview_impact_open_title} from './typography/kinetic-type/impact-open-title/Preview';
import {meta as meta_impact_open_title} from '../../../assets/visual-kit/templates/typography/kinetic-type/impact-open-title/Template';
import {Preview as Preview_keyword_pop_highlight} from './typography/kinetic-type/keyword-pop-highlight/Preview';
import {meta as meta_keyword_pop_highlight} from '../../../assets/visual-kit/templates/typography/kinetic-type/keyword-pop-highlight/Template';
import {Preview as Preview_lead_word_zoom_assemble} from './typography/kinetic-type/lead-word-zoom-assemble/Preview';
import {meta as meta_lead_word_zoom_assemble} from '../../../assets/visual-kit/templates/typography/kinetic-type/lead-word-zoom-assemble/Template';
import {Preview as Preview_line_by_line_slide} from './typography/kinetic-type/line-by-line-slide/Preview';
import {meta as meta_line_by_line_slide} from '../../../assets/visual-kit/templates/typography/kinetic-type/line-by-line-slide/Template';
import {Preview as Preview_outline_box_title} from './typography/kinetic-type/outline-box-title/Preview';
import {meta as meta_outline_box_title} from '../../../assets/visual-kit/templates/typography/kinetic-type/outline-box-title/Template';
import {Preview as Preview_per_character_rise} from './typography/kinetic-type/per-character-rise/Preview';
import {meta as meta_per_character_rise} from '../../../assets/visual-kit/templates/typography/kinetic-type/per-character-rise/Template';
import {Preview as Preview_quote_bracket_pull} from './typography/kinetic-type/quote-bracket-pull/Preview';
import {meta as meta_quote_bracket_pull} from '../../../assets/visual-kit/templates/typography/kinetic-type/quote-bracket-pull/Template';
import {Preview as Preview_quote_card} from './typography/kinetic-type/quote-card/Preview';
import {meta as meta_quote_card} from '../../../assets/visual-kit/templates/typography/kinetic-type/quote-card/Template';
import {Preview as Preview_slab_punch_title} from './typography/kinetic-type/slab-punch-title/Preview';
import {meta as meta_slab_punch_title} from '../../../assets/visual-kit/templates/typography/kinetic-type/slab-punch-title/Template';
import {Preview as Preview_soft_blur_in} from './typography/kinetic-type/soft-blur-in/Preview';
import {meta as meta_soft_blur_in} from '../../../assets/visual-kit/templates/typography/kinetic-type/soft-blur-in/Template';
import {Preview as Preview_speed_slab_title} from './typography/kinetic-type/speed-slab-title/Preview';
import {meta as meta_speed_slab_title} from '../../../assets/visual-kit/templates/typography/kinetic-type/speed-slab-title/Template';
import {Preview as Preview_split_text_stagger} from './typography/kinetic-type/split-text-stagger/Preview';
import {meta as meta_split_text_stagger} from '../../../assets/visual-kit/templates/typography/kinetic-type/split-text-stagger/Template';
import {Preview as Preview_step_flow_horizontal} from './typography/kinetic-type/step-flow-horizontal/Preview';
import {meta as meta_step_flow_horizontal} from '../../../assets/visual-kit/templates/typography/kinetic-type/step-flow-horizontal/Template';
import {Preview as Preview_title_demote_to_label} from './typography/kinetic-type/title-demote-to-label/Preview';
import {meta as meta_title_demote_to_label} from '../../../assets/visual-kit/templates/typography/kinetic-type/title-demote-to-label/Template';
import {Preview as Preview_tracking_in} from './typography/kinetic-type/tracking-in/Preview';
import {meta as meta_tracking_in} from '../../../assets/visual-kit/templates/typography/kinetic-type/tracking-in/Template';
import {Preview as Preview_type_contrast_emphasis} from './typography/kinetic-type/type-contrast-emphasis/Preview';
import {meta as meta_type_contrast_emphasis} from '../../../assets/visual-kit/templates/typography/kinetic-type/type-contrast-emphasis/Template';
import {Preview as Preview_typewriter_reveal} from './typography/kinetic-type/typewriter-reveal/Preview';
import {meta as meta_typewriter_reveal} from '../../../assets/visual-kit/templates/typography/kinetic-type/typewriter-reveal/Template';
import {Preview as Preview_word_slot_cycle} from './typography/kinetic-type/word-slot-cycle/Preview';
import {meta as meta_word_slot_cycle} from '../../../assets/visual-kit/templates/typography/kinetic-type/word-slot-cycle/Template';
import {Preview as Preview_curtain_push} from './typography/before-after/curtain-push-compare/Preview';
import {meta as meta_curtain_push} from '../../../assets/visual-kit/templates/typography/before-after/curtain-push-compare/Template';
import {Preview as Preview_era_photo} from './media-display/before-after/era-photo-compare/Preview';
import {meta as meta_era_photo} from '../../../assets/visual-kit/templates/media-display/before-after/era-photo-compare/Template';
export const TemplateRegistry: React.FC = () => <>
  <Folder name="Templates">
    <Folder name="Typography">
      <Folder name="Emphasis">
        <Composition id="Templates-Typography-Emphasis-converging-arrows" component={Preview_converging_arrows} width={1280} height={720} fps={30} durationInFrames={meta_converging_arrows.durationInFrames} />
        <Composition id="Templates-Typography-Emphasis-corner-bracket-frame" component={Preview_corner_bracket_frame} width={1280} height={720} fps={30} durationInFrames={meta_corner_bracket_frame.durationInFrames} />
        <Composition id="Templates-Typography-Emphasis-hand-drawn-ellipse" component={Preview_hand_drawn_ellipse} width={1280} height={720} fps={30} durationInFrames={meta_hand_drawn_ellipse.durationInFrames} />
        <Composition id="Templates-Typography-Emphasis-ink-underline" component={Preview_ink_underline} width={1280} height={720} fps={30} durationInFrames={meta_ink_underline.durationInFrames} />
        <Composition id="Templates-Typography-Emphasis-quote-hold-arrow" component={Preview_quote_hold_arrow} width={1280} height={720} fps={30} durationInFrames={meta_quote_hold_arrow.durationInFrames} />
        <Composition id="Templates-Typography-Emphasis-strike-and-replace" component={Preview_strike_and_replace} width={1280} height={720} fps={30} durationInFrames={meta_strike_and_replace.durationInFrames} />
      </Folder>
      <Folder name="KineticType">
        <Composition id="Templates-Typography-KineticType-alt-block-lines" component={Preview_alt_block_lines} width={1280} height={720} fps={30} durationInFrames={meta_alt_block_lines.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-count-badge-title" component={Preview_count_badge_title} width={1280} height={720} fps={30} durationInFrames={meta_count_badge_title.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-countdown-arc-scatter" component={Preview_countdown_arc_scatter} width={1280} height={720} fps={30} durationInFrames={meta_countdown_arc_scatter.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-error-retype" component={Preview_error_retype} width={1280} height={720} fps={30} durationInFrames={meta_error_retype.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-flying-words" component={Preview_flying_words} width={1280} height={720} fps={30} durationInFrames={meta_flying_words.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-impact-open-title" component={Preview_impact_open_title} width={1280} height={720} fps={30} durationInFrames={meta_impact_open_title.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-keyword-pop-highlight" component={Preview_keyword_pop_highlight} width={1280} height={720} fps={30} durationInFrames={meta_keyword_pop_highlight.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-lead-word-zoom-assemble" component={Preview_lead_word_zoom_assemble} width={1280} height={720} fps={30} durationInFrames={meta_lead_word_zoom_assemble.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-line-by-line-slide" component={Preview_line_by_line_slide} width={1280} height={720} fps={30} durationInFrames={meta_line_by_line_slide.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-outline-box-title" component={Preview_outline_box_title} width={1280} height={720} fps={30} durationInFrames={meta_outline_box_title.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-per-character-rise" component={Preview_per_character_rise} width={1280} height={720} fps={30} durationInFrames={meta_per_character_rise.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-quote-bracket-pull" component={Preview_quote_bracket_pull} width={1280} height={720} fps={30} durationInFrames={meta_quote_bracket_pull.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-quote-card" component={Preview_quote_card} width={1280} height={720} fps={30} durationInFrames={meta_quote_card.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-slab-punch-title" component={Preview_slab_punch_title} width={1280} height={720} fps={30} durationInFrames={meta_slab_punch_title.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-soft-blur-in" component={Preview_soft_blur_in} width={1280} height={720} fps={30} durationInFrames={meta_soft_blur_in.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-speed-slab-title" component={Preview_speed_slab_title} width={1280} height={720} fps={30} durationInFrames={meta_speed_slab_title.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-split-text-stagger" component={Preview_split_text_stagger} width={1280} height={720} fps={30} durationInFrames={meta_split_text_stagger.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-step-flow-horizontal" component={Preview_step_flow_horizontal} width={1280} height={720} fps={30} durationInFrames={meta_step_flow_horizontal.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-title-demote-to-label" component={Preview_title_demote_to_label} width={1280} height={720} fps={30} durationInFrames={meta_title_demote_to_label.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-tracking-in" component={Preview_tracking_in} width={1280} height={720} fps={30} durationInFrames={meta_tracking_in.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-type-contrast-emphasis" component={Preview_type_contrast_emphasis} width={1280} height={720} fps={30} durationInFrames={meta_type_contrast_emphasis.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-typewriter-reveal" component={Preview_typewriter_reveal} width={1280} height={720} fps={30} durationInFrames={meta_typewriter_reveal.durationInFrames} />
        <Composition id="Templates-Typography-KineticType-word-slot-cycle" component={Preview_word_slot_cycle} width={1280} height={720} fps={30} durationInFrames={meta_word_slot_cycle.durationInFrames} />
      </Folder>
    </Folder>
    <Folder name="BeforeAfter">
      <Composition id="Templates-Typography-BeforeAfter-curtain-push-compare" component={Preview_curtain_push} schema={z.object({palette: z.enum(PALETTE_IDS)})} defaultProps={{palette: DEFAULT_PALETTE_ID}} width={1920} height={1080} fps={30} durationInFrames={meta_curtain_push.durationInFrames} />
    </Folder>
    <Folder name="MediaDisplay">
      <Folder name="BeforeAfter">
        <Composition id="Templates-MediaDisplay-BeforeAfter-era-photo-compare" component={Preview_era_photo} schema={z.object({palette: z.enum(PALETTE_IDS)})} defaultProps={{palette: DEFAULT_PALETTE_ID}} width={1920} height={1080} fps={30} durationInFrames={meta_era_photo.durationInFrames} />
      </Folder>
    </Folder>
    <Folder name="Diagram">
      <Folder name="DataChart">
        <Composition id="Templates-Diagram-DataChart-bar-chart-growth" component={Preview_bar_chart_growth} width={1280} height={720} fps={30} durationInFrames={meta_bar_chart_growth.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-chart-grow" component={Preview_chart_grow} width={1280} height={720} fps={30} durationInFrames={meta_chart_grow.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-chip-grid-single-select" component={Preview_chip_grid_single_select} width={1280} height={720} fps={30} durationInFrames={meta_chip_grid_single_select.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-info-term-card" component={Preview_info_term_card} width={1280} height={720} fps={30} durationInFrames={meta_info_term_card.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-line-chart-story-draw" component={Preview_line_chart_story_draw} width={1280} height={720} fps={30} durationInFrames={meta_line_chart_story_draw.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-map-route-pin" component={Preview_map_route_pin} width={1280} height={720} fps={30} durationInFrames={meta_map_route_pin.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-metric-with-sparkline" component={Preview_metric_with_sparkline} width={1280} height={720} fps={30} durationInFrames={meta_metric_with_sparkline.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-number-counter" component={Preview_number_counter} width={1280} height={720} fps={30} durationInFrames={meta_number_counter.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-number-slab-pop" component={Preview_number_slab_pop} width={1280} height={720} fps={30} durationInFrames={meta_number_slab_pop.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-numbered-step-stack" component={Preview_numbered_step_stack} width={1280} height={720} fps={30} durationInFrames={meta_numbered_step_stack.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-source-converge" component={Preview_source_converge} width={1280} height={720} fps={30} durationInFrames={meta_source_converge.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-step-timeline-vertical" component={Preview_step_timeline_vertical} width={1280} height={720} fps={30} durationInFrames={meta_step_timeline_vertical.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-ui-prop-theater" component={Preview_ui_prop_theater} width={1280} height={720} fps={30} durationInFrames={meta_ui_prop_theater.durationInFrames} />
        <Composition id="Templates-Diagram-DataChart-unit-grid-proportion" component={Preview_unit_grid_proportion} width={1280} height={720} fps={30} durationInFrames={meta_unit_grid_proportion.durationInFrames} />
      </Folder>
    </Folder>
  </Folder>
</>;
