# Glassify UI Re-skin — Design

**Date:** 2026-08-08
**Status:** Approved

## Goal

Convert the solid-panel synthwave UI into heavy glassmorphism: frosted translucent surfaces over an animated neon ambience, keeping the existing palette, fonts, and accent gradients.

## Ambience (layout)

Fixed `-z-10` layer in `app/layout.tsx`: three blurred neon blobs (cyan / pink / purple) with slow drift animations (`drift-a/b/c`), a faint dotted grid overlay fading from the top, and a vignette. Disabled under `prefers-reduced-motion`.

## Tokens (globals.css)

- `--surface` → `rgba(255,255,255,0.07)`, `--surface-hover` → `0.13`, `--border` → `0.18` — every existing `bg-surface` panel becomes translucent automatically.
- New `.glass-panel` (24px blur + saturation, glow shadow), `.glass-bar` (darker translucent bar for header/footer).
- `.glow-card`: glass + blur, top-edge sheen (`::after`), hover lift, stronger glow shadow; existing conic border animation kept.
- `.btn-primary`: same purple→pink gradient, now with neon halo glow + hover lift. `.btn-ghost` and `.input-field`: translucent white at 5% with 12% borders, 8px blur.

## Sweep

All `bg-surface border border-border rounded-xl` panels (39 in 23 files + components: AccountForm, ReviewForm, ProductCard, WishlistButton, mobile menu) now use `glass-panel`/`glow-card`. Header/footer → `glass-bar`.

## Verification

`tsc --noEmit`, `eslint`, and `npm run build` all pass.