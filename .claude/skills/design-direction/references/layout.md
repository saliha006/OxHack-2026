# Layout, spacing, rhythm

Evidence and sources: `Claude instructions/research-ledger.md` §3 design + audit → "Layout".

## 1. Spacing system
- One scale on a 4 px base: `4 8 12 16 24 32 48 64 96 (128)`. Carbon and Material both use 4/8-based scales; 4 vs 8 is preference (4 helps dense UI and text).
- Semantic names (`--space-2xs … --space-3xl`) or the framework's scale (Tailwind). No arbitrary values (`13px`, `gap-[7px]`).
- **Proximity carries meaning:** space inside a group < space between groups. Labels sit closer to their own field than to the next one; headings closer to their section than to the previous one. Proximity can outweigh colour and shape as a grouping cue.
- **Rhythm:** tight groupings (8–16) + generous separations (48–96 on brand pages, 24–48 in product UI). Equal spacing everywhere = no hierarchy.
- Use `gap` for sibling spacing; `clamp()` for section padding that breathes on large screens (brand surfaces).

## 2. Structure
- **Flexbox** for one dimension (toolbars, button rows, card internals); **Grid** for two (page shells, dashboards, galleries). Named `grid-template-areas` for complex pages.
- **Container queries** for components (Baseline widely available since 2025), media queries for the page shell. **Subgrid** to align card internals across a row.
- Breakpoints where the **content** breaks (measure goes out of 45–75ch, nav stops fitting), not at device widths.
- Content max-width for reading (≈ 65ch for text columns; ~1100–1400 px for app shells). Full-bleed moments are deliberate, not the default.
- Semantic z-index scale (`dropdown < sticky < overlay < modal < toast < tooltip`); never `9999`. Prefer the top layer (`<dialog>`, `popover`) so menus don't get clipped by `overflow` containers.

## 3. Hierarchy and scanning
- **Squint test:** blurred, you can still see the #1 thing, the #2 things, and the groups.
- People scan: F-pattern is the failure mode when text has no structure; layer-cake (scanning headings) is what good structure enables. Front-load: the key point first; headings that start with information-carrying words; lists; descriptive links.
- One primary action per view. Secondary actions visibly quieter.
- Alignment: pick a dominant left edge; centre only short, symmetrical content (hero lines, empty states). Long centred text is hard to read.
- Optical fixes: icons and play/arrow glyphs often need nudging; large display text may need a small negative indent to align visually.

## 4. Components and density
- **Cards** suit heterogeneous, browsable items. Use lists or tables for homogeneous, comparable, ranked or searchable data. Never nest cards. A row of identical icon + heading + text cards is the most common generated-layout tell; vary structure by what each section needs.
- **Bento grids** have no usability evidence; treat as decoration that must still pass the card rules.
- **Dashboards:** one glanceable screen for the key question; quantities as position/length (bars, lines); avoid pies/donuts/gauges, 3D, colour-for-magnitude. Big-number "hero metrics" only with real data and context (vs. period, target).
- Density follows the register: data tools can be dense (compact rows, 13–14 px secondary text), marketing pages airy. Dense ≠ cramped: keep ≥ 8 px padding inside bordered/filled containers.
- Choice count: don't cap options at a magic number (choice-overload effects average near zero across studies). Reduce options when they're hard to compare; otherwise group, order, and set a sensible default.

## 5. Responsive
- Mobile-first CSS (`min-width` queries). Layouts **compose differently** across sizes, not just shrink: sidebar → drawer/bottom nav, table → stacked rows with labels, multi-column form → one column.
- Inputs: `@media (pointer: coarse)` for larger targets, `@media (hover: hover)` for hover-only niceties; never put function behind hover.
- Safe areas on phones: `env(safe-area-inset-*)` with `viewport-fit=cover`.
- Test at 320, 375, 768, 1024, 1440 px and 200% zoom; check long words, long names, and translations (+30–40% length).

## 6. Depth and shape
- One radius scale tied to component size/role (e.g. 4 inputs, 8 cards, 999 pills); the same radius on everything is a tell.
- **Concentric radii:** a rounded element nested in a rounded container uses outer radius = inner radius + padding (+ border). Past ~24 px of padding, treat them as separate surfaces.
- Headings get more space above than below, so they bind to the content they introduce.
- One elevation scale, subtle and layered; elevation communicates layering (menus, dialogs), not decoration. Dark mode: lighter surfaces instead of shadows.
- Borders sparingly: spacing and background shifts often separate better. No thick single-side accent stripes on cards.

## 7. Checklist
- [ ] Spacing from the scale only; groups tighter than gaps between groups
- [ ] One primary action per view; squint test passes
- [ ] Cards only where content is heterogeneous; no nested cards
- [ ] Reflows at 320 px without horizontal scroll; composes (not shrinks) at each size
- [ ] Radius/elevation scales tied to role
