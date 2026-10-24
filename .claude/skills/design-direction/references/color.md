# Colour: OKLCH, tokens, dark mode, use-case palettes

Evidence and sources: `Claude instructions/research-ledger.md` §3 design + audit → "Colour".

## 1. Work in OKLCH
- `oklch(L C H)`: L 0–1 is perceptual lightness, so equal L steps *look* equal across hues; HSL's L does not (HSL "50%" yellow is far lighter than "50%" blue). Supported for ~95% of users; relative colour syntax ~93%; `color-mix()` is Baseline.
- **Gamut:** max chroma depends on hue *and* lightness (≤ ~0.37 even in P3). Browsers clip out-of-gamut values, which shifts hue. Keep base tokens sRGB-safe; put wider-gamut variants inside `@media (color-gamut: p3)`. `scripts/oklch_palette.py` gamut-maps by reducing chroma (the CSS Color 4 method).
- **OKLCH L is not WCAG luminance.** Two colours at the same L can have different contrast. Always compute the WCAG 2 ratio (`scripts/contrast_check.py`).
- Gradients between distant hues: interpolate `in oklab` (or add a middle stop) to avoid muddy or hue-swinging midpoints. Some blues drift toward cyan as L changes; check by eye.

## 2. Build ramps, then roles
- **Ramp:** fix the hue, step L (≈ 0.98 → 0.15), give each step a chosen chroma that **tapers toward both ends** (high chroma at very light/dark L looks garish or is out of gamut). Choosing max-chroma per step makes uneven ramps.
- **Neutrals:** 9–11 steps, tinted 0.005–0.015 C toward *the brand's* hue, or C = 0 for true grey. Don't tint warm or cool by reflex: the warm "cream/sand/parchment" body background (L 0.84–0.97, C < 0.06, H 40–100) is a 2025–26 generated-UI tell.
- **One accent ramp.** Add a second hue only for a real job (data categories, a secondary brand colour). Accents earn attention because they're rare: actions, selection, focus, key data. "60-30-10" is interior-design folklore with no evidence base; the defensible core is just *use the accent sparingly*.
- **Semantic roles** (separate from brand): success, warning, danger, info. Each paired with an icon + text, never colour alone (WCAG 1.4.1). If the brand hue is near red/green, move the brand or the status hue so they never collide.

### Token layers
1. **Primitives**: `--neutral-50…950`, `--accent-50…950` (raw OKLCH).
2. **Semantic roles**: `--color-bg`, `--color-surface`, `--color-ink`, `--color-ink-muted`, `--color-border` (decorative), `--color-border-strong` (controls, ≥ 3:1), `--color-accent`, `--color-on-accent`, `--color-success|warning|danger|info`, `--color-focus`.
3. **Component tokens** only where a component truly needs its own (`--button-primary-bg: var(--color-accent)`).

Components use roles, never primitives or hex. Themes redefine only layer 2. For tool interchange, the W3C Design Tokens format (DTCG 2025.10, stable) is JSON with `$value`/`$type` and `{alias}` references (`*.tokens.json`).

States without new colours: `oklch(from var(--color-accent) calc(l - 0.06) c h)` for hover/pressed, or `color-mix(in oklch, var(--color-accent) 85%, black)`. Re-check contrast after.

## 3. Dark mode
- `color-scheme: light dark` on `:root` (plus `<meta name="color-scheme" content="light dark">`) so form controls and scrollbars follow. `light-dark(a, b)` is Baseline 2024 (~91%); keep a `prefers-color-scheme` block as fallback.
- Follow the OS by default; if you add a toggle, remember the choice. Don't make dark the only theme for a general audience (light wins for reading accuracy for most people; dark helps some low-vision users), so offer both when you can.
- **Background ≈ L 0.18–0.21, not #000.** Pure black on glossy screens is harsh; most users and design systems prefer near-black.
- **Text ≈ L 0.92–0.94, not pure white.** Reduce weight slightly or add 0.05 line-height for long light-on-dark text.
- **Elevation = lighter surface** (+0.03–0.05 L per level), not shadow. Components never darker than the background.
- **Accents lighter and slightly less chromatic** than in light mode. Re-check every pair; a passing light-mode pair says nothing about dark.

## 4. Starting palettes for common use cases
Starting points, not templates: change the hue to the brand's. All values sRGB-safe; ratios are WCAG 2 against bg (or bg / surface). `border` is decorative (exempt); input/control outlines use `border-strong` (≥ 3:1). Pair every status colour with an icon + text.

### a) SaaS / developer tool (restrained, cool neutral, blue accent)
| Token | Light | Ratio | Dark | Ratio |
|---|---|---|---|---|
| bg | 0.985 0.002 260 | – | 0.19 0.006 260 | – |
| surface | 1 0 0 | – | 0.235 0.008 260 | – |
| ink | 0.21 0.015 260 | 17.0 | 0.93 0.006 260 | 15.0 |
| ink-muted | 0.50 0.015 260 | 5.7 | 0.72 0.012 260 | 7.5 |
| border-strong | 0.62 0.012 260 | 3.5 | 0.54 0.012 260 | 3.7 |
| accent | 0.52 0.19 265 | 5.5 | 0.72 0.14 265 | 7.3 |
| on-accent | 0.99 0.003 265 | 5.6 | 0.18 0.03 265 | 7.5 |
| success / warning / danger | 0.50 0.12 150 · 0.55 0.12 70 · 0.53 0.19 27 | 5.4 · 4.8 · 5.6 | 0.75 0.14 150 · 0.80 0.13 75 · 0.70 0.17 25 | 8.8 · 9.7 · 6.4 |
Blue is the category reflex for dev tools: keep it only if the brand wants it; the structure works with any hue.

### b) Consumer / lifestyle / brand (warm neutral, committed accent)
| Token | Light | Ratio | Dark | Ratio |
|---|---|---|---|---|
| bg | 0.98 0.008 75 | – | 0.20 0.01 50 | – |
| surface | 1 0 0 | – | 0.245 0.012 50 | – |
| ink | 0.22 0.02 50 | 16.4 | 0.94 0.01 75 | 15.2 |
| ink-muted | 0.49 0.02 50 | 6.0 | 0.74 0.015 60 | 7.8 |
| border-strong | 0.62 0.014 60 | 3.5 | 0.55 0.014 55 | 3.7 |
| accent | 0.55 0.17 35 | 5.0 | 0.74 0.14 40 | 7.5 |
| on-accent | 0.99 0.005 75 | 5.1 | 0.18 0.03 40 | 7.8 |
| success / warning / danger | 0.50 0.11 155 · 0.55 0.12 65 · 0.52 0.19 25 | 5.4 · 4.7 · 5.7 | 0.76 0.13 155 · 0.81 0.13 75 · 0.71 0.16 25 | 8.9 · 9.9 · 6.6 |
Brand surfaces may go **committed** (accent carries 30–60% of a hero) or **drenched** (the surface is the colour). Accent hue 35 sits near danger 25: never show both without icons, or move one. Warmth via imagery and type, not by defaulting the bg to cream.

### c) Data dashboard (neutral chrome, data carries colour)
| Token | Light | Ratio | Dark | Ratio |
|---|---|---|---|---|
| bg | 0.97 0.003 250 | – | 0.18 0.005 250 | – |
| surface | 1 0 0 | – | 0.225 0.007 250 | – |
| ink | 0.22 0.01 250 | 15.9 | 0.93 0.005 250 | 15.3 |
| ink-muted | 0.50 0.012 250 | 5.5 | 0.72 0.01 250 | 7.6 |
| border-strong | 0.62 0.01 250 | 3.3 | 0.54 0.01 250 | 3.7 |
| accent | 0.50 0.105 235 | 5.4 | 0.74 0.12 230 | 8.4 |
| success / warning / danger | 0.50 0.12 155 · 0.55 0.12 70 · 0.53 0.18 27 | 5.2 · 4.6 · 5.3 | 0.75 0.13 155 · 0.80 0.13 75 · 0.70 0.16 25 | 8.9 · 9.9 · 6.6 |
- **Categorical series** (Okabe–Ito, colour-vision-deficiency safe), in order: `#0072B2` blue, `#E69F00` orange, `#009E73` bluish green, `#D55E00` vermilion, `#CC79A7` reddish purple, `#56B4E9` sky blue. Max 6–7 series, then "Other". On white, orange (2.3:1) and sky blue (2.3:1) fail the 3:1 graphics rule: add a darker outline or direct labels; drop yellow `#F0E442` on light backgrounds.
- **Sequential:** one hue, L 0.95 → 0.35, chroma peaking mid-ramp. **Diverging:** two hues (e.g. blue H≈250 ↔ orange H≈55) with a light neutral midpoint. Never red↔green.
- Vary lightness between series so the chart still reads in greyscale; label lines directly instead of relying on a legend.

### d) Health / finance / public service (trust through legibility)
| Token | Light | Ratio | Dark | Ratio |
|---|---|---|---|---|
| bg | 1 0 0 | – | 0.19 0.008 245 | – |
| surface | 0.975 0.004 240 | – | 0.235 0.01 245 | – |
| ink | 0.20 0.012 245 | 18.1 | 0.94 0.004 245 | 15.5 |
| ink-muted | 0.46 0.015 245 | 7.1 | 0.76 0.01 245 | 8.6 |
| border (all, ≥ 3:1) | 0.62 0.012 245 | 3.6 | 0.55 0.012 245 | 3.8 |
| accent | 0.46 0.11 245 | 7.1 | 0.75 0.11 240 | 8.4 |
| success / warning / danger | 0.48 0.11 155 · 0.52 0.11 65 · 0.50 0.18 27 | 6.2 · 5.7 · 6.6 | 0.77 0.12 155 · 0.82 0.12 75 · 0.72 0.15 25 | 9.4 · 10.4 · 7.0 |
Trust comes from legibility, explicit states and restraint (the GOV.UK pattern), not from "blue = trust". Aim near AAA (7:1) for body text; make every form-field border ≥ 3:1; use a high-visibility focus style (e.g. yellow `#ffdd00` fill with a dark underline, focus only).

## 5. Myths not to design by
- **Colour-psychology dictionaries** ("blue = trust", "red = urgency"): the evidence is early, small-sample and context-dependent, and associations vary by culture. Choose colour for function and brand fit.
- **APCA as the WCAG 3 standard:** APCA was removed from the WCAG 3 draft (2023); WCAG 3's contrast method is undecided. You can use APCA Lc (≈ 75 body, 60 large/UI, 45 large display) as an extra design check, but WCAG 2 ratios are the pass/fail gate.
- **"Pure grey is dead" / "alpha is a design smell":** taste rules, not laws. Zero-chroma neutrals are fine; alpha is fine for overlays and states. Just check contrast after compositing.

## 6. Checklist
- [ ] Hue chosen from the brief/brand, written in the direction contract with a reason
- [ ] Ramps tapered and in sRGB gamut; roles defined; components use roles only
- [ ] Every text/bg pair ≥ 4.5:1 (large ≥ 3:1), every control boundary and focus indicator ≥ 3:1, in **both** themes
- [ ] No colour-only meaning; status = colour + icon + text
- [ ] Dark: bg L ≈ 0.18–0.21, text L ≈ 0.92–0.94, elevation by lighter surfaces
- [ ] Charts: ≤ 7 CVD-safe categories, greyscale-readable, labelled
