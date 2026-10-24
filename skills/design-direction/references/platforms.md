# Platform conventions (native-feeling UI)

When the target is a native app, or a web/PWA that must feel at home on a phone, the platform's conventions beat originality for **structure and interaction**. Brand expresses through colour, type in display moments, imagery, copy and motion character.

## iOS / iPadOS (Apple HIG)
- Layout inside safe-area insets (notch, Dynamic Island, home indicator). Web: `viewport-fit=cover` + `env(safe-area-inset-*)`.
- Navigation: tab bar for 2–5 top-level sections (sections, not actions); push navigation for hierarchy; sheets for self-contained tasks. Never disable edge-swipe back.
- Type: system text styles via Dynamic Type; SF Pro for UI text, brand face for display moments only. Body 17 pt.
- Targets ≥ 44×44 pt. System controls (switch, segmented control, picker, action sheet, context menu). SF Symbols for icons.
- Colour: semantic system colours; one tint colour for interactive elements; dark appearance designed, not inverted. System materials for translucency (not hand-rolled glass); honour Reduce Transparency and Increase Contrast.

## Android (Material 3)
- Navigation bar (3–5 destinations) on compact widths; navigation rail/drawer on expanded. Predictive Back must work.
- Edge-to-edge with window insets (status bar, nav bar, cutout, keyboard).
- Type: Material type roles (display/headline/title/body/label); `sp` units; brand face themed in through the scale.
- Targets ≥ 48×48 dp with ≥ 8 dp gaps. Material components (filled/tonal/outlined/text buttons, one FAB max, snackbars, bottom sheets).
- Colour: Material colour roles; Dynamic Color where it fits, with a static brand fallback; tonal elevation.

## Web that feels native (PWA, mobile web)
- Respect `prefers-color-scheme`, `prefers-reduced-motion`, `prefers-contrast`, `prefers-reduced-transparency`.
- Inputs ≥ 16 px font-size (smaller triggers iOS zoom-on-focus); correct `type`, `inputmode`, `autocomplete`, `enterkeyhint`.
- Primary actions within thumb reach on phones; bottom sheets over tiny dropdowns for long option lists.
- Don't fake platform chrome (fake iOS status bars, fake Android nav). Don't mix iOS and Material controls on one surface.

Cross-platform apps: decide whether the app adapts per OS (Cupertino on iOS, Material on Android) or carries one brand look; either way, keep the OS guarantees (back gesture, insets, text scaling, reduced motion) on both. Audit with `ui-audit/references/native.md`.
