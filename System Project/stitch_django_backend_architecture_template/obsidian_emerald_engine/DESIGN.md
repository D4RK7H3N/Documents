---
name: Obsidian Emerald Engine
colors:
  surface: '#0f141b'
  surface-dim: '#0f141b'
  surface-bright: '#343941'
  surface-container-lowest: '#090f15'
  surface-container-low: '#171c23'
  surface-container: '#1b2027'
  surface-container-high: '#252a32'
  surface-container-highest: '#30353d'
  on-surface: '#dee2ec'
  on-surface-variant: '#b9cbbd'
  inverse-surface: '#dee2ec'
  inverse-on-surface: '#2c3138'
  outline: '#849588'
  outline-variant: '#3b4a3f'
  surface-tint: '#00e38f'
  primary: '#cdffdc'
  on-primary: '#003920'
  primary-container: '#00f59b'
  on-primary-container: '#006b41'
  inverse-primary: '#006d42'
  secondary: '#a9cfba'
  on-secondary: '#133728'
  secondary-container: '#2b4e3e'
  on-secondary-container: '#98bea9'
  tertiary: '#caffe1'
  on-tertiary: '#003824'
  tertiary-container: '#61efb2'
  on-tertiary-container: '#006b48'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#53ffab'
  primary-fixed-dim: '#00e38f'
  on-primary-fixed: '#002111'
  on-primary-fixed-variant: '#005231'
  secondary-fixed: '#c4ebd6'
  secondary-fixed-dim: '#a9cfba'
  on-secondary-fixed: '#002114'
  on-secondary-fixed-variant: '#2b4e3e'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#0f141b'
  on-background: '#dee2ec'
  surface-variant: '#30353d'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: -0.005em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: -0.01em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 15px
    letterSpacing: -0.01em
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 12px
    letterSpacing: 0.06em
  kbd-badge:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 12px
    letterSpacing: 0em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.75rem
  gutter-mobile: 0.5rem
  margin: 1rem
  margin-mobile: 0.75rem
  space-xs: 0.125rem
  space-sm: 0.25rem
  space-md: 0.5rem
  space-lg: 0.75rem
  space-xl: 1rem
---

## Brand & Style

This design system targets backend engineers, site reliability teams, and technical administrators operating critical infrastructure and data platforms. The personality is hyper-focused, surgical, and robust—engineered for low cognitive overhead during high-stakes triage, schema migrations, and high-frequency administrative operations.

The aesthetic fuses modern developer tooling (Linear, Raycast, Vercel) with the foundational heritage of Django's administrative paradigm. It leans on an ultra-dark slate palette, fine 1-pixel structural containment, tactical luminous emerald accents, and an unapologetic respect for density and monospaced data clarity. Motion is instantaneous (sub-150ms transitions), chrome is muted to elevate operational data, and interactions prioritize keyboard ergonomics across every view.

## Colors

The palette establishes an aggressive visual hierarchy tailored for nocturnal operations and prolonged terminal-like focus:

- **Canvas & Structural Layers**: 
  - Base canvas sits at `#0c1017`.
  - Secondary containers and sidebars anchor at `#161b22`.
  - Surface elevations, elevated popovers, and table headers utilize `#21262d`.
  - Structural separators and grid rules strictly utilize `#30363d` (1px solid).
  - Hover states on rows and items use an ultra-subtle wash of `#30363d` at 40% opacity (`rgba(48, 54, 61, 0.4)`).

- **Brand & Signal Colors**:
  - **Action Mint (`#00f59b`)**: Primary interactive triggers, active caret states, critical focus rings, and real-time live-connection beacons.
  - **Django Deep Emerald (`#092e20`)**: Anchor tint for active navigation backgrounds, badge backdrops, and selected rows.
  - **Teal / Emerald Mid (`#10b981`)**: Informational status indicators, secondary confirmations, and execution graphs.

- **Status & Telemetry**:
  - Error / Rollback: `#f85149` (crimson).
  - Warning / Migrations Pending: `#f0883e` (amber).
  - Muted Text / Meta: `#8b949e`.
  - Body Text / Contrast: `#c9d1d9`.
  - High-Contrast Code / Titles: `#f0f6fc`.

## Typography

Typography enforces strict operational rigor through a clean dual-font pairing:

1. **Inter** powers primary narrative text, model labels, field descriptions, and navigation menus. Weights are confined to 400 (regular), 500 (medium), and 600 (semi-bold) to maintain razor-sharp rendering on subpixel display surfaces.
2. **JetBrains Mono** governs machine data: primary keys (UUIDs/IDs), ISO timestamps, SQL queries, raw JSON payloads, terminal outputs, query counts, and keyboard shortcut chips.

Scale transitions remain tight and dense. Body text is pinned to an optimal technical height of 13px with an 18px line height, keeping large database rows vertically compact while preserving horizontal scanning speed.

## Layout & Spacing

The control plane implements a dense fluid architecture engineered for maximum screen efficiency:

- **Grid & Shell Model**: A fixed-width left rail (240px collapsable to 56px icon-only), an optional model-tree/filter sub-panel (220px), and a fluid primary canvas stretching across the viewport width.
- **Micro-Spacing Cadence**: All spatial relationships follow a strict 4px grid. Standard padding within data cells is 6px vertical by 12px horizontal (`space-sm` / `space-lg`). Component internal gaps adhere to 4px (`space-sm`) and 8px (`space-md`).
- **Breakpoints**:
  - `Desktop (> 1280px)`: Full multi-pane workflow (Navigation + Model Filters + Tabular View + Inspector Drawer).
  - `Tablet (768px - 1279px)`: Model filters collapse to modal dialogs; tabular data horizontally scrolls with sticky primary key columns.
  - `Mobile (< 767px)`: Rail collapses to an off-canvas drawer; inspection panes take 100% viewport width via bottom sheets.

## Elevation & Depth

This system avoids heavy, diffused dropshadows. Depth is articulated through **tonal planar stepping**, **1px precision hairpins**, and **frosted translucency**:

- **Ground (Level 0)**: Viewport background at `#0c1017`.
- **Level 1 (Panels & Canvases)**: `#161b22` bounded by 1px solid `#30363d`.
- **Level 2 (Popovers, Tooltips, Command Palette)**: `#21262d` bounded by 1px solid `#484f58` accompanied by an ultra-sharp shadow: `0 8px 24px -4px rgba(0, 0, 0, 0.65), 0 1px 2px 0 rgba(0, 0, 0, 0.8)`.
- **Glass Headers & App Bars**: `rgba(12, 16, 23, 0.75)` backdrop blur with `backdrop-filter: blur(12px)` and a bottom border of `1px solid rgba(48, 54, 61, 0.6)`.
- **Active Focus Indicator**: No offset rings. Active inputs and table cells receive an inner focus outline of `1px solid #00f59b` with an emerald glow: `box-shadow: 0 0 0 1px #00f59b, 0 0 8px -2px rgba(0, 245, 155, 0.4)`.

## Shapes

The design system employs a crisp, technical shape profile:

- **Base Radius (`roundedness: 1`)**: Standard buttons, input elements, code blocks, and table cells carry a tight 4px (`0.25rem`) radius.
- **Nested & Container Radius (`rounded-lg`)**: Cards, modals, drawers, and the command palette carry an 8px (`0.5rem`) boundary radius.
- **Pills / Status Badges**: Exceptionally set to `9999px` strictly for health tags, running workers, and boolean condition pills to stand apart from rectangular structural data.

## Components

### Buttons
- **Primary Action**: Background `#00f59b`, foreground `#092e20` (bold weight), border `none`. Hover shifts to `#10b981`. Focused with `0 0 0 2px rgba(0, 245, 155, 0.35)`.
- **Secondary / Subdued**: Background `#21262d`, foreground `#c9d1d9`, border `1px solid #30363d`. Hover brings `#30363d` background and `#f0f6fc` text.
- **Destructive**: Background `transparent`, foreground `#f85149`, border `1px solid rgba(248, 81, 73, 0.4)`. Hover fills `rgba(248, 81, 73, 0.1)`.

### Tabular Data Grid (Django Change List)
- Header row height is fixed at 32px with `#161b22`, text in uppercase `label-caps` (`#8b949e`), and sorting toggles.
- Data rows sit at 34px height. Alternating backgrounds are avoided in favor of 1px border dividers (`#21262d`) and instantaneous hover illumination (`rgba(48, 54, 61, 0.3)`).
- Checkbox selections highlight entire rows with `rgba(0, 245, 155, 0.05)` and a left-anchored 2px stripe of `#00f59b`.

### Keyboard Shortcut Chips (`<kbd>`)
- Sized strictly with `kbd-badge` typography. Background `#161b22`, border `1px solid #30363d`, text `#8b949e`, subtle inner shadow. Rendered alongside commands (e.g., `⌘K`, `G then D`, `⇧A`).

### Command Palette (⌘K)
- Centered modal container (`rounded-lg`, width 640px) at `#161b22` with a frosted outer backdrop (`rgba(0, 0, 0, 0.7)`).
- Input field at top: borderless, height 48px, 14px font, accompanied by real-time model search, recent queries, and action shortcuts.

### Inputs & Filters
- Background `#0c1017`, border `1px solid #30363d`, height 28px for compact density. Font set to `code-md` for precision query writing.
- Clear indicators with trailing icons for fast reset.

### Status Pills & Indicators
- Live status uses a 6px breathing dot with ping animation (`#00f59b`), surrounded by a pill container (`#092e20`, text `#00f59b`, 1px border `rgba(0, 245, 155, 0.2)`).