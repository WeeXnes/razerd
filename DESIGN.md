# OpenProStreet design principles

These rules cover both the stats site and the control panel, which should look like one product.
The direction is black, monochrome and precise, in the spirit of Coder and Ollama. Don't copy their
logos, wording or artwork.

## The five rules

1. **Black first.** The page is true black. Depth comes from hairlines and one or two near-black
   surfaces, not from shadows.
2. **Colour is information.** The interface itself is white and grey. Colour appears only when it
   means something: race type, medal, status. If removing a colour loses no meaning, remove it.
3. **Type does the work.** Hierarchy comes from size, weight and white versus grey. Numbers are the
   heroes of this product, so they get the largest, cleanest treatment.
4. **Fewer boxes.** Use whitespace and hairline dividers before reaching for a card. Don't nest a
   card inside a card.
5. **Quiet precision.** Everything aligns to the grid, numbers line up in columns, and nothing is
   there only for decoration.

## Never

- Gradients of any kind, including the bar under the header.
- Drop shadows, glows, or coloured backgrounds on large areas.
- A blue or other brand accent. The primary action is white.
- Filled coloured pills on navigation, or solid coloured table rows.
- Emoji as icons, or animation that moves layout.

## Tokens

Use these names in both projects. Dark is the default and doesn't follow the operating system.

```css
:root {
  --bg: #000000;          /* the page */
  --surface: #0a0a0a;     /* cards, table headers, inputs */
  --surface-2: #141414;   /* hover and selected */
  --line: #1f1f1f;        /* hairlines */
  --line-strong: #333333; /* input borders, secondary buttons */
  --text: #fafafa;        /* headings, values */
  --text-2: #a3a3a3;      /* body text */
  --text-3: #808080;      /* labels, hints; the dimmest allowed for text */
  --invert: #fafafa;      /* primary button background */
  --on-invert: #000000;   /* primary button text */

  --success: #4ade80;
  --warning: #fbbf24;
  --danger: #f87171;

  --grip: #8ab4f8;
  --drift: #f28fb8;
  --drag: #f5a66a;
  --speed: #b79cff;
  --gold: #e8c547;
  --silver: #c4c4c4;
  --bronze: #c98d5e;

  color-scheme: dark;
}

:root[data-theme='light'] {
  --bg: #ffffff;
  --surface: #fafafa;
  --surface-2: #f0f0f0;
  --line: #e8e8e8;
  --line-strong: #cccccc;
  --text: #0a0a0a;
  --text-2: #525252;
  --text-3: #6b6b6b;
  --invert: #0a0a0a;
  --on-invert: #ffffff;

  --success: #15803d;
  --warning: #a16207;
  --danger: #b91c1c;

  --grip: #1d4ed8;
  --drift: #be185d;
  --drag: #c2410c;
  --speed: #6d28d9;
  --gold: #8a6500;
  --silver: #6b6b6b;
  --bronze: #92552a;

  color-scheme: light;
}
```

The theme toggle has two choices, Dark and Light. Light is a straight inversion of the same design,
not a separate look. `theme-color` is `#000000`.

## Type

- **Fonts:** Geist for text and Geist Mono for numbers and labels, installed from
  `@fontsource-variable/geist` and `@fontsource-variable/geist-mono`. They are bundled with the site,
  so the browser still makes no outside requests. Fall back to `system-ui`.
- **Body:** 15px, line height 1.6, `--text-2`.
- **Page title:** `clamp(2rem, 4vw, 3rem)`, weight 500, letter spacing `-0.03em`, `--text`.
- **Section title:** 1.25rem, weight 500, letter spacing `-0.01em`, `--text`.
- **Micro label:** Geist Mono, 11px, uppercase, letter spacing `0.08em`, `--text-3`. Use it for table
  headers, stat labels and section eyebrows.
- **Numbers:** Geist Mono with `font-variant-numeric: tabular-nums`, so columns line up.
- **Hero stats:** big number above a small label, in the style of `9M+ / installs a month`. No box
  around them, with hairlines between them.

## Layout

- **Width:** content up to 1120px, centred. Forms up to 640px.
- **Spacing:** multiples of 4px. Leave 64px or more between major sections on desktop.
- **Phones:** 16px side gutter at 375px wide, with no horizontal page scroll. Wide tables scroll
  inside their own container.
- **Radius:** 12px for cards and lists, 10px for inputs, full pill for buttons, 6px for small tags.

## Components

- **Header:** 60px, sticky, `--bg`, one hairline below, no gradient. A plain wordmark on the left:
  `OpenProStreet` in `--text` at weight 600, then a `--text-3` slash and the app name (`Stats` or
  `Panel`). Navigation is plain text in `--text-2`; hover and active are `--text`, with no filled
  background.
- **Footer:** a hairline and one line of `--text-3` text.
- **Primary button:** pill, `--invert` background, `--on-invert` text, weight 500, 36px high. Use at
  most one per view.
- **Secondary button:** pill, transparent, `--line-strong` border, `--text`.
- **Danger button:** like secondary, with `--danger` text. It fills only on hover.
- **Lists and tables:** one hairline-bordered container with `--line` dividers between rows, in the
  style of Ollama's model list. Micro labels for column headers, right-aligned numbers, `--surface-2`
  on hover.
- **Inputs:** `--surface` background, `--line-strong` border, 10px radius, 40px high, labels above.
  On focus the border turns `--text`.
- **Tags:** 6px radius, 1px `--line-strong` border, transparent, `--text-2`. A race type is a 6px dot
  in its colour next to `--text-2` text, never a filled pill.
- **Medals:** the number in `--gold`, `--silver` or `--bronze`. No filled circle.
- **Status:** a 6px dot in `--success`, `--warning` or `--danger`, next to text. Never colour alone.
- **Empty states:** one quiet line and, where useful, one action. No illustrations.
- **Focus:** `outline: 2px solid var(--text); outline-offset: 2px` on `:focus-visible`, everywhere.
- **Motion:** 120ms on colour and opacity only. Turn it off under `prefers-reduced-motion`.

## Accessibility

All text meets WCAG AA in both themes, every control works by keyboard, and meaning is never carried
by colour alone.
