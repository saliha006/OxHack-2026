# Extraction recipes (run in the page)

Each recipe is a zero-arg function. It works as Chrome DevTools MCP `evaluate_script`, Playwright `page.evaluate(fn)`, or pasted into the console.
Method adapted from jakubkrehel/skills `explain-interface` (MIT), https://github.com/jakubkrehel/skills, and re-written here.
The outputs are **evidence to read, not code to paste into our repo.**

## 1. Layer search: which properties paint the effect (elements and pseudo-elements)
```js
() => {
  const idle = v => !v || ['none','normal','1','blur(0px)','auto'].includes(v);
  const P = ['backgroundImage','filter','backdropFilter','mixBlendMode','maskImage','boxShadow','clipPath','opacity'];
  const out = [];
  for (const el of document.querySelectorAll('*')) for (const ps of [null,'::before','::after']) {
    const s = getComputedStyle(el, ps), f = {};
    for (const p of P) { const v = p==='maskImage' ? (s.maskImage||s.webkitMaskImage) : s[p]; if (!idle(v)) f[p] = String(v).slice(0,180); }
    const k = Object.keys(f); if (!k.length || (k.length===1 && f.opacity)) continue;
    const r = el.getBoundingClientRect(), h = getComputedStyle(el);
    out.push({ tag: el.tagName.toLowerCase(), ps: ps||'el', cls: (el.getAttribute('class')||'').slice(0,80),
      pos: h.position, z: h.zIndex, box: `${r.width|0}x${r.height|0}@${r.left|0},${r.top|0}`, f });
  }
  return { vw: innerWidth, n: out.length, hits: out.slice(0,120) };
}
```
How to read it:
- A box wider than `vw`, or with a negative offset, is oversized on purpose so its edges never show.
- `backdropFilter` means the layer *below* is part of the effect.
- `mixBlendMode` means the colour depends on what's underneath.
- DOM order ≈ paint order within a stacking context.

## 2. Is it canvas / WebGL / video instead of CSS?
```js
() => ({
  libs: performance.getEntriesByType('resource').map(r=>r.name).filter(n=>/three|ogl|pixi|regl|babylon|spline|rive|lottie|gsap|motion/i.test(n)),
  media: [...document.querySelectorAll('canvas,svg,video,img')].slice(0,40).map(el=>{const r=el.getBoundingClientRect();
    return {tag:el.tagName.toLowerCase(), box:`${r.width|0}x${r.height|0}@y${r.top|0}`,
      ctx: el.tagName==='CANVAS' ? (el.getContext('2d') ? '2d-or-unused' : 'webgl-or-other') : null,
      src:(el.currentSrc||el.getAttribute('src')||'').slice(0,90)};}),
})
```
Run it only **after** the page has drawn, because probing an unused canvas creates a 2D context on it. A WebGL canvas plus a shader lib means a shader. Describe the look and stop there; don't lift the shader. Video plus a sticky container usually means scroll-scrubbed media. A canvas fed by a numbered image sequence is the Apple-style flipbook (CSS-Tricks, 2020).

## 3. What paints at one pixel
```js
() => { const x = 720, y = 300;  // edit the coordinates
  return document.elementsFromPoint(x,y).slice(0,8).map(el=>{const s=getComputedStyle(el);
    return {tag:el.tagName.toLowerCase(), cls:(el.getAttribute('class')||'').slice(0,60),
      bg:s.backgroundImage.slice(0,80), filter:s.filter, backdrop:s.backdropFilter, blend:s.mixBlendMode, pe:s.pointerEvents};}); }
```
The list is front-to-back. It **skips `pointer-events:none`** layers, which is common for decoration, so cross-check with recipe 1.

## 4. Timing: everything currently animating (CSS animations + transitions + WAAPI)
```js
() => document.getAnimations().slice(0,30).map(a=>{const t=a.effect?.getTiming?.()||{}, el=a.effect?.target;
  return {el: el?.tagName?.toLowerCase(), cls:(el?.getAttribute?.('class')||'').slice(0,50),
    name: a.animationName || a.transitionProperty || '(waapi/js)', dur:t.duration, delay:t.delay, easing:t.easing, iter:t.iterations,
    kf:(a.effect?.getKeyframes?.()||[]).map(({offset,easing,opacity,transform,filter,clipPath})=>({offset,easing,opacity,transform,filter,clipPath}))};})
```
- The result is empty at rest. Trigger the state first (hover tool, scroll into view, reload) and run it *during* the motion.
- CSS animations carry easing **per keyframe**. The effect-level easing reads `linear`.
- Different `delay`s across siblings mean a stagger. Report the rule (first, last, step).
- rAF-driven JS animation is invisible here. Use a performance trace, or REA `observe_web_execution` / `inspect_web_event_listeners`.

## 5. Hover/focus diff for one element
```js
() => { const el = document.querySelector('SELECTOR');  // edit the selector
  const keys = ['color','backgroundColor','backgroundImage','boxShadow','transform','filter','borderColor','outline','transition'];
  const s = getComputedStyle(el); return Object.fromEntries(keys.map(k=>[k,s[k]])); }
```
Run once at rest and once after the `hover` / `press_key Tab` tool, then diff. `transition` gives you the property list, durations and easings.

## 6. Tokens and type used near the effect
```js
() => { const r = getComputedStyle(document.documentElement); const vars = {};
  for (const sh of document.styleSheets) { try { for (const ru of sh.cssRules) if (ru.selectorText===':root') for (const p of ru.style) if (p.startsWith('--')) vars[p]=r.getPropertyValue(p).trim(); } catch(e){ /* cross-origin sheet */ } }
  return { count: Object.keys(vars).length, sample: Object.entries(vars).slice(0,80) }; }
```
A `catch` hit means a cross-origin stylesheet, so say "unreadable" rather than guessing. Use their tokens only to understand their *system* (scale ratios, step sizes). Never import their values.

## Network assets (identify, don't download into our repo)
DevTools MCP `list_network_requests` / `get_network_request` lists fonts (woff2), images, videos, Lottie/Rive JSON and shaders. Use it to name the *kind* of asset and its weight, which feeds the perf budget. Fonts and media from their CDN are never committed to our repo.

## Rebuild checklist (map each spec line to our code)
- Layer → our element or pseudo-element, plus our token.
- Easing → our easing token (or propose one).
- Duration → our duration scale.
- Stagger → a CSS `--i` index or the motion lib's stagger.
- Reduced motion → opacity-only variant.
- Hover → also `:focus-visible`.
- Loops → paused off-screen.
- New dependency → ask the user first.
