# Testing tools and manual protocol

**Coverage reality:** automated rules find a minority to about half of issues. Deque measures ~57% by issue *volume*. Counted by WCAG *criteria*, it's ~20–30%. In the GDS 2017 study the best single tool found 37–41% of planted barriers. A Lighthouse 100 is achievable on an unusable site. Always do the manual pass and say what wasn't tested.

## Automated

### Anti-pattern + quality detector (bundled)
See `anti-patterns.md`. `node <ui-audit>/scripts/detector/detect-antipatterns.mjs --json <path>`.

### axe-core via Playwright (preferred: real rendering, scriptable flows)
```bash
npm i -D @playwright/test @axe-core/playwright
npx playwright install chromium
```
```js
// a11y.spec.js
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

for (const path of ['/', '/signup']) {
  test(`axe ${path}`, async ({ page }) => {
    await page.goto(`http://localhost:3000${path}`);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze();
    console.log(JSON.stringify(results.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length })), null, 2));
    expect(results.violations).toEqual([]);
  });
}
```
Also run it after opening menus/dialogs and in dark mode (`page.emulateMedia({ colorScheme: 'dark' })`) and reduced motion (`{ reducedMotion: 'reduce' }`). axe aims for zero false positives, so its violations are usually real. Its "incomplete" items need a human.

### Lighthouse
`npx lighthouse <url> --only-categories=accessibility --output=json --output-path=./lh.json` (or Chrome DevTools → Lighthouse). The score is a weighted subset of axe rules; its 10 "manual checks" are unscored. Never quote the score as conformance.

### Pa11y (CI-friendly, two engines)
`npm i -g pa11y` (v10 needs Node ≥ 22.13), then `pa11y <url> --runner axe --runner htmlcs --standard WCAG2AA`. `pa11y-ci` for multiple URLs.

### Browser + annotation tools (if connected)
- **Chrome DevTools MCP**: `lighthouse_audit`, `evaluate_script` / `get_css_styles` for computed values, `performance_start_trace`. Never `pkill chrome`: it kills the MCP's own browser.
- **Agentation** (user runs it in their app): they click elements and you get selectors, source paths and computed styles. Good for "this one looks off" reports.
- **Rams** (rams.ai): scored design review per PR, criticals cap the score. Free on one public repo, paid beyond.

### Contrast
`python <ui-audit>/scripts/contrast_check.py "#777" "#fff"`; `--min 3` for large text/UI; `--pairs file.txt` (fg and bg separated by a tab or 2+ spaces). APCA (advisory only): apcacontrast.com.

## Manual protocol (do in this order)
1. **Keyboard:** unplug the mouse mentally. Tab / Shift+Tab through the whole flow; Enter/Space activate; arrows inside tabs, menus, radios, listboxes; Esc closes overlays; focus returns to the trigger. Note: traps, unreachable controls, invisible focus, illogical order, focus hidden under sticky UI.
2. **Screen reader** (if available): NVDA + Firefox/Chrome (Windows), VoiceOver + Safari (macOS: Cmd+F5; iOS), TalkBack (Android). Navigate by headings (NVDA `H`, VoiceOver rotor), landmarks (`D` / rotor), form fields (`F`), links list (NVDA `Insert+F7`). Listen for: unnamed controls ("button"), missing state ("expanded/collapsed"), silent async updates, decorative noise. If no screen reader: inspect the browser's accessibility tree (DevTools → Accessibility) and say so under "Not covered".
3. **Zoom & reflow:** 200% browser zoom; viewport 320 px wide; text-spacing override (line-height 1.5, letter 0.12em, word 0.16em, paragraph 2em) via devtools CSS.
4. **Colour:** greyscale screenshot (meaning survives?); devtools "Emulate vision deficiencies"; dark theme; forced colours (`forced-colors: active` emulation or Windows contrast themes).
5. **Motion:** emulate `prefers-reduced-motion: reduce`; look for parallax, large slides, auto-play, flashing.
6. **Pointer/touch:** measure target boxes (devtools box model); try drag alternatives; check nothing is hover-only on a touch device/emulator.
7. **Forms:** submit empty, submit wrong formats, go back/forward, paste into password/OTP, use autofill.
8. **Content & states:** empty, loading (throttle network to "Slow 3G"), error (block a request in devtools), long strings, RTL (`dir="rtl"` on `<html>`).

Record per check: done / not possible (why). That line goes into the audit's "Not covered".
