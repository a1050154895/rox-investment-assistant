# ROX UI 2.0 Design System

## Product Direction

ROX is an evidence-first investment research workspace. The interface should help a user answer four questions quickly:

1. What changed?
2. What evidence supports it?
3. What should I verify next?
4. Is my decision still valid?

The visual language is **Strategic Studio**: a calm research room with the information density of a terminal and the restraint of an editorial notebook.

## Visual Principles

- Evidence before decoration.
- One clear primary action per view.
- Warm ink surfaces, vermilion for decisions, indigo for structure.
- Data freshness is always visible and never conveyed by color alone.
- Desktop supports comparison; mobile supports one decision at a time.
- Cards frame tools and repeated items, not entire page sections.
- Motion is brief and functional; reduced-motion users get the same information.

## Color System

### Surfaces

- `--bg-page`: deep ink black with a warm neutral cast.
- `--bg-surface`: charcoal ink for primary work surfaces.
- `--bg-elevated`: raised ink for controls and nested evidence.
- `--bg-paper`: warm off-white reserved for exported or shareable research artifacts.

### Semantic accents

- Vermilion: primary action, decision, selected state.
- Indigo: methodology, structure, navigation.
- Amber: stale or needs verification.
- Sage: valid, available, or completed.
- Neutral gray: unavailable or not evaluated. Never use red for missing data.

Chinese market price colors remain red-up/green-down inside market-specific components only. They do not control general risk or brand semantics.

## Typography

- Display: system Chinese sans with strong line height, no negative tracking.
- Body: readable system sans, 14px minimum on mobile.
- Numbers: monospace with consistent decimal formatting.
- Metadata: 11-12px, never used as the only place for a critical instruction.

## Layout

- Desktop: 12-column comparison grid, 16px base gap, max content width 1440px.
- Mobile: single-column task flow, 12px page gutter, 44px minimum touch targets.
- Primary task first: Today -> Research -> Decision -> Review.
- Details are disclosed through native disclosure, drawers, and progressive steps.

## Core Components

- `EvidenceBadge`: source, observation date, freshness, and status.
- `DecisionAction`: one primary action plus secondary low-emphasis actions.
- `ResearchStep`: one focused question per mobile step.
- `StatusTag`: text plus color plus shape; never color alone.
- `MetricBlock`: value, label, time context, and source state.
- `EvidenceDrawer`: source, transmission path, affected industry, and next validation action.

## Acceptance

- 375, 390, and 414px: no horizontal overflow.
- Mobile primary controls: at least 44px high.
- Keyboard focus is visible.
- Loading, empty, stale, unavailable, and error states are explicit.
- Lighthouse mobile accessibility >= 0.85 and best practices >= 0.85.
- Playwright covers registration -> research card -> review.
