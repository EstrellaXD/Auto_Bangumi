# Design

Visual system of the AutoBangumi web UI (Vue 3 + naive-ui + UnoCSS). Source of truth for tokens: `webui/src/style/var.scss` (`:root` light, `.dark` overrides). naive-ui components are themed via `GlobalThemeOverrides` in `webui/src/App.vue`, which reference these same CSS custom properties.

## Color

Strategy: **Soft Ink** — near-monochrome ink on soft neutral fills. Color never carries text; it appears only as small marks and on a short list of interactive states.

Where purple is allowed: primary buttons, focus rings, switch/checkbox-on, the active-tab underline, selected states. Where semantic color is allowed: small square status/tag marks (~7–10px, 2–2.5px radius), error borders/text on invalid fields, destructive buttons. Everything else is ink (`--color-text*`) on neutral surfaces.

| Token | Light | Role |
|---|---|---|
| `--color-primary` | `#6C4AB6` | Primary actions, focus, on-states, selection |
| `--color-primary-hover` | `#563A92` | Hover on primary |
| `--color-primary-light` | `#E8DEF8` | Selected/tinted backgrounds |
| `--color-primary-alpha` | `rgba(108,74,182,.2)` | Focus rings |
| `--color-accent` | `#F97316` | Sparse highlight (calendar today) |
| `--color-success` | `#22C55E` | Status marks: healthy/running |
| `--color-danger` | `#EF4444` | Status marks, errors, destructive actions |
| `--color-warning` | `#F59E0B` | Status marks: needs-review/degraded |
| `--color-bg` | `#FAFAFA` | App background |
| `--color-surface` | `#FFFFFF` | Cards, panels, bars |
| `--color-surface-2` | `#F1F4F8` | Filled controls and list rows (borderless) |
| `--color-text` | `#1E293B` | Body text |
| `--color-text-secondary` | `#64748B` | Secondary text |
| `--color-text-muted` | `#94A3B8` | Muted text — decorative only, not for body copy (fails 4.5:1) |
| `--color-border` | `#E2E8F0` | Hairlines (chips, alerts, dividers) |

Dark theme overrides the same custom properties under `.dark` on `<html>`; never hard-code theme-specific colors in components.

Anti-patterns (rejected as AI-generic, do not reintroduce): pastel pill badges with colored text on tinted fills, tinted alert boxes with icons, icon-in-a-rounded-square empty states, floating-thumb segmented controls, glowing status dots.

## Typography

One family: `Inter, -apple-system, 'Noto Sans SC', 'Microsoft YaHei', system-ui, sans-serif` (`--font-family`). Fixed rem scale, tight ratio; no display face. CJK fallback quality is a requirement, not an afterthought.

Data text — feed sources, timestamps, episode markers (E08), speeds, hashes — sets in `--font-mono` with `font-variant-numeric: tabular-nums`. Content titles (CJK) may carry weight (600–650); UI labels stay at 500 and below.

## Spacing & Layout

Mobile-first tokens: `--layout-padding` 12→14→16px, `--layout-gap` 10→12px across breakpoints (`forTablet`/`forDesktop` SCSS mixins). Bars: `--topbar-height` 48px, `--nav-height` 56px, `--touch-target` 44px. Desktop: sidebar + content; mobile: bottom nav.

## Radius, Shadow, Motion

- Radius scale (Soft Ink): `--radius-sm` 4px (all controls) · `--radius-md` 8px (cards, menus, modals) · `--radius-lg` 12px (sheets) · `--radius-xl` 16px · `--radius-full` (switch rail only).
- Shadows: `--shadow-sm/md/lg`, all soft black at ≤10% alpha; no colored glows.
- Motion: `--transition-fast` 150ms / `--transition-normal` 200ms / `--transition-slow` 300ms, all `ease-out`. Motion conveys state only.

## Z-index

Semantic scale only: `--z-dropdown` 10 · `--z-sticky` 20 · `--z-fixed` 30 · `--z-modal-backdrop` 40 · `--z-modal` 50 · `--z-popover` 60 · `--z-tooltip` 70. Never arbitrary values.

## Components

- **Universal `ab-*` layer** (`src/components/basic/`): pages and composites use only `ab-*` components — never raw `NButton`/`NInput`/bare styled `<button>`. Where naive-ui fits, the `ab-*` component wraps it (`ab-select`, `ab-switch`, `ab-tooltip`); where it doesn't, the component is custom on tokens (`ab-button`, `ab-tag`, `ab-modal`).
- **Composites**: app-specific `ab-*` components (`ab-add-rss`, `ab-edit-rule`, calendar pieces, layout shells) compose the universal layer + tokens.
- **Utility CSS**: UnoCSS with attributify preset; prefer token-backed values over arbitrary literals.
- Every interactive component ships all states: default, hover, focus-visible, active, disabled, loading, error — and ≥44px touch targets on mobile (`--touch-target`).
- Soft Ink component grammar: filled controls on `--color-surface-2` (border only on focus/error); tags are hairline chips with a square semantic mark and ink text; status is a square mark + ink label; tabs underline (no thumb); alerts are hairline outlines led by a bold colored word (no icons, no tinted fills); toasts are inverted ink chips; empty states are left-aligned prose with one action; loading is skeletons, not spinners-in-content.
- Every universal component ships a Storybook story and (where it has behavior) a vitest test in `__tests__/`.

The universal set (`src/components/basic/` unless noted):

| Group | Components |
|---|---|
| Actions | `ab-button` (primary/secondary/ghost/danger·sm/md·loading), `ab-icon-button` (required label, 44px touch, ghost/solid/round), `ab-menu` (headlessui dropdown), `ab-split-button` |
| Forms | `ab-field` (label/description/error/required + aria wiring via injection), `ab-input` (affixes, clearable, password reveal, error), `ab-select`, `ab-switch`, `ab-segmented` (underline tabs), `ab-setting` (root — field+control settings row) |
| Overlays | `ab-modal` (adaptive: dialog ≥ tablet, bottom sheet on mobile; footer slot; sizes sm/md/lg), `useConfirm()` + `ab-confirm-host` (promise confirm, danger variant), `ab-tooltip`, `ab-bottom-sheet` (internal to ab-modal) |
| Display | `ab-tag` (semantic marks: success/warning/danger/info/neutral, closable), `ab-status` (running/stopped/paused/degraded + label/detail), `ab-badge` (count/dot, 99+), `ab-container` (root — title/footer/flush card), `ab-fold-panel` (root — accessible, animated), `ab-progress` |
| Data & feedback | `ab-list` (selection, loading skeleton, density comfortable/compact, empty slot), `ab-toolbar` (search/filters/actions), `ab-alert` (hairline, bold lead word), toast via `useMessage()` (inverted ink), `ab-empty`, `ab-skeleton` (lines/row/card), `ab-pull-refresh` |
| Page chrome | `ab-page-title`, `ab-search`, `ab-status-bar` (root), layout shells |

Retired (do not reintroduce): `ab-popup`, `ab-adaptive-modal`, `ab-label`, `ab-setting`'s type-switch-only API, `ab-add`, `ab-button-multi`, `ab-data-list`, `ab-image`, `ab-rule`, `ab-swipe-container`, and the `ab-input` UnoCSS attribute shortcut.

## Voice

UI copy through i18n only (`src/i18n/en.json` + `zh-CN.json`, keys always added in pairs). Sentence case in English. Labels are nouns, buttons are verbs, errors say what to do next.
