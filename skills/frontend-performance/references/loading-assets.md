# Loading: images, fonts, JavaScript

Sources: web.dev Optimize LCP, browser-level lazy-loading, fetch priority, font best practices;
Chrome "Improved font fallbacks"; caniuse AVIF; Alex Russell "The Performance Inequality Gap, 2026"
(Nov 2025). Ledger: `Claude instructions/research-ledger.md` §4 motion + performance.

## Images
- **Formats:** AVIF (Chrome 85+, Firefox 93+, Safari 16.4+) with WebP/JPEG fallback via `<picture>`.
- **Size:** `srcset` + accurate `sizes`; never ship a 3000 px image into a 300 px slot.
- **LCP image:** in the HTML (not injected by JS), `fetchpriority="high"`, **never** `loading="lazy"`,
  and don't combine `lazy` with `fetchpriority="high"`. Use high priority on 1–2 images max.
  CSS-background hero → `<link rel="preload" as="image" fetchpriority="high">`.
- **Below the fold:** `loading="lazy"` + `decoding="async"`.
- **Always** `width`/`height` or `aspect-ratio` (CLS).
```html
<picture>
  <source type="image/avif" srcset="hero-800.avif 800w, hero-1600.avif 1600w" sizes="(max-width: 800px) 100vw, 800px">
  <img src="hero-800.jpg" srcset="hero-800.jpg 800w, hero-1600.jpg 1600w" sizes="(max-width: 800px) 100vw, 800px"
       width="1600" height="900" alt="…" fetchpriority="high">
</picture>
```
- **Animated GIFs** → `<video autoplay muted loop playsinline>` instead (Vercel guidelines; far smaller files).
- **Video backgrounds:** `muted playsinline`, poster image, `preload="none"` below the fold, pause
  off-screen and under reduced motion.

## Fonts
- WOFF2 only; subset; ≤ 2 families, few weights (or one variable font).
- Body text: `font-display: optional` (no swap shift). Brand/display: `swap`, with a metric-matched
  fallback to kill the shift:
```css
@font-face { font-family: "Brand Fallback"; src: local("Arial");
  size-adjust: 104%; ascent-override: 92%; descent-override: 24%; line-gap-override: 0%; }
body { font-family: "Brand", "Brand Fallback", sans-serif; }
```
- Preload only the 1–2 fonts used above the fold (`crossorigin` required); preload ignores `unicode-range`.

## JavaScript
- **Budgets** (Russell 2026, 3 s target on a Galaxy A24-class phone over 9 Mbps / 100 ms RTT,
  compressed critical-path bytes): content/markup-heavy page ≈ 2.0 MiB total incl. ≈ 300 KiB JS;
  JS-heavy app ≈ 1.2 MiB total incl. ≈ 620 KiB JS. Median mobile JS is ≈ 680 KiB — most sites are over.
  Expert heuristic, single author: use as a budget starting point, not law.
- Split by route; dynamic-import heavy, below-the-fold or interaction-only widgets (charts, editors,
  WebGL scenes, motion libraries used only on one page).
- Third parties first: audit tag managers, chat widgets, A/B scripts; load after interaction or
  use facades. They are the usual INP killers.
- Ship less hydration: server-render static content; islands/partial hydration where the framework
  supports it.
- Prefer CSS (transitions, `@starting-style`, scroll-driven, view transitions) over animation
  libraries for simple motion; a library you load for one fade is pure cost.
- Analyse with the framework's bundle analyzer; check `Coverage` in DevTools for unused JS/CSS.

## Network hints
- `preconnect` to the 1–2 critical third-party origins; `dns-prefetch` for the rest.
- Don't `preload` speculatively — it competes with the LCP resource.
- HTTP caching with immutable hashed assets.
