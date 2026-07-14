# Appliora — Design System

This documents the visual system that already exists in the codebase
(`frontend/src/index.css`, `mascot.css`, `Mascot.jsx`, `public/favicon.svg`)
and formalizes it into a token set. **Extend this, don't compete with it.**
If you're about to design a new screen or component, read this first —
don't invent a new visual language for it.

## Style direction

Warm Minimalist Consumer SaaS. Audience is friends casually sharing job
links with each other — not an enterprise tool, not a public job board. The
interface should feel personable and encouraging, not dense or neutral.
The mascot ("Applio") carries the product's personality; the rest of the UI
stays calm and gets out of its way. Don't add decorative motion or heavy
styling to cards/buttons on top of the mascot — that's double-counting the
"delight" budget and will read as busy.

## Theme: Ocean (resolved 2026-07-15)

The original palette had drifted into two different purples (logo/mascot
violet `#7c3aed` vs. UI chrome indigo `#4f46e5`). Resolved by moving to a
single **ocean teal/cyan** accent applied everywhere — logo, mascot
hoodie/glow/particles/confetti, and all UI chrome — rather than picking one
of the two old purples. Semantic status colors (danger/ok/warn) were left
alone; only the brand/neutral palette changed. Character identity (hair,
skin, eyes) on the mascot was also left alone — only its clothing and the
decorative UI elements shifted.

```
--bg:           #eef6f9   (was #f4f5fb)
--ink:          #12303b   (was #1c1e26)
--muted:        #5c7480   (was #6b7080)
--line:         #d6e4e9   (was #e3e5ef)
--accent:       #0891b2   (was #4f46e5 — chrome — and #7c3aed — logo/mascot)
--accent-dark:  #0e7490   (was #4338ca / #6d28d9)
--accent-soft:  #e0f7fa   (was #eef0ff)
--expired:      #5c7480   (was #6b7080)
--expired-soft: #eaf1f3   (was #f1f2f6)
```

Mascot decorative accents (`Mascot.jsx`) mapped from the old violet family
to ocean cyan/teal/blue: `#7c3aed`→`#0891b2`, `#6d28d9`→`#0e7490`,
`#a78bfa`→`#5eead4`, `#8b5cf6`→`#06b6d4`, `#f472b6`→`#2dd4bf`. `#60a5fa`
(blue) and `#fbbf24` (amber, confetti accent) were kept as-is — both
already read as "ocean" (water blue / sunlight-on-water gold). The success
checkmark stays green (`#22c55e`) — success shouldn't stop reading as
success just because the brand hue changed.

Verified live: dev server driven with Playwright (headless Chromium),
screenshots taken of idle/waving, searching, found-draft, happy/shared, and
focus states, plus a real end-to-end share of a live Greenhouse job
posting. No console errors, no leftover purple/indigo, focus ring and
status badges render correctly against the new background.

Dark mode: still no token scaffolding. Scope it as a `PRD.md` task if
wanted, rather than half-adding it ad hoc.

## Tokens

Source of truth: `:root` in `frontend/src/index.css`. Components must
reference these, not hardcode one-off values — the type scale in
particular was fragmented (nine distinct ad hoc font sizes existed before
this scale was added) and shouldn't grow a tenth.

```css
/* color — ocean theme */
--bg: #eef6f9;             --accent: #0891b2;      --danger: #dc2626;
--surface: #ffffff;       --accent-dark: #0e7490; --ok: #047857;
--ink: #12303b;           --accent-soft: #e0f7fa; --ok-soft: #ecfdf5;
--muted: #5c7480;         --line: #d6e4e9;        --warn: #b45309;
--expired: #5c7480;                               --warn-soft: #fffbeb;
--expired-soft: #eaf1f3;

/* spacing — 4px base */
--space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
--space-5: 20px; --space-6: 24px; --space-7: 32px; --space-8: 40px;
--space-10: 48px; --space-12: 64px;

/* type scale */
--text-xs: 0.75rem;   --text-sm: 0.8125rem; --text-base: 0.875rem;
--text-md: 0.9375rem; --text-lg: 1.0625rem; --text-xl: 1.25rem;
/* weights: 400 body, 600 semibold (buttons/labels), 700 bold (headings) */
/* family: 'Segoe UI', system-ui, -apple-system, sans-serif — no webfont, by design */

/* radius */
--radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px; --radius-full: 999px;

/* shadow */
--shadow-sm: 0 1px 3px rgba(28, 30, 38, 0.08);
--shadow-md: 0 4px 14px rgba(28, 30, 38, 0.14);

/* motion */
--duration-fast: 150ms; --duration-base: 280ms; --duration-slow: 450ms;
--ease-standard: ease;
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1); /* used for pop-in effects */
```

## Component rules (already established — follow, don't reinvent)

- **Cards**: white surface, 1px `--line` border, `--radius-lg`, `--shadow-sm`.
- **Primary button**: solid `--accent`, white text, semibold, darkens to
  `--accent-dark` on hover, `--radius-md`.
- **Ghost button**: transparent, `--muted` text, `--line` border.
- **Inputs**: white surface, `--line` border, `--radius-md`; focus state is
  `--accent` border + `--accent-soft` glow ring — never a default browser
  outline, never no visible focus state.
- **Status/tonal badges** (deadline urgency today; extraction confidence in
  Phase 2 of `PRD.md` tomorrow): soft background + saturated text of the
  same hue (`--ok-soft`/`--ok`, `--warn-soft`/`--warn`, etc.), `--radius-full`
  pill shape. Reuse this pattern for any new status indicator instead of
  inventing a new one.
- **Empty states**: dashed border, not solid — visually distinct from a
  populated card.

## Motion

The mascot's mood transitions (float, blink, wave, particle-rise, confetti)
are the app's primary motion language. Everything else is restrained:
short transitions on hover/focus, no decorative animation. Keep it that
way. `prefers-reduced-motion: reduce` must be respected by anything new
that animates — see the existing handling in `mascot.css` for the pattern.

## Accessibility baseline

- Visible focus state on every interactive element (already the case via
  `--accent-soft` ring — don't remove it for aesthetics).
- Icon-only buttons need a real `aria-label`, not just `title` (currently a
  gap on the delete `✕` button — screen readers may not reliably announce
  `title`). Fix opportunistically when touching that component.
- Status conveyed by color (deadline badges) also has a text label
  ("Apply by ...", "Closed ...") — never color alone. Keep that pattern for
  any new status UI.

## Responsive strategy

Mobile-first already: flex-wrap and `grid-template-columns:
repeat(auto-fit, minmax(220px, 1fr))` reflow naturally without
breakpoint-specific rewrites. One explicit breakpoint (`560px`) stacks the
header inputs full-width. `max-width: 860px` on `.page` means no ultra-wide
handling is needed — content centers with margin, which is correct for a
single-column feed at any width beyond tablet. New screens should follow
this same "let flex/grid reflow, add a breakpoint only where it visibly
breaks" approach rather than pre-emptively adding breakpoints.

## Open decisions (don't resolve unilaterally)

1. ~~Unify the two-purple accent~~ — resolved 2026-07-15, see "Theme:
   Ocean" above.
2. Dark mode: no token scaffolding exists yet. Scope it as a task in
   `PRD.md` if/when it's wanted, rather than half-adding it ad hoc.
