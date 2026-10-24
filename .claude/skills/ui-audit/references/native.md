# Native app audit (iOS / Android / cross-platform)

Use instead of the web tooling when the target is SwiftUI/UIKit, Jetpack Compose/Views, React Native, Expo or Flutter shipping native UI. The detector and axe do not apply; audit from source and, if available, a simulator/device with the platform accessibility inspector (Xcode Accessibility Inspector, Android Accessibility Scanner / TalkBack).

## Checks
| Area | iOS (HIG) | Android (Material 3) |
|---|---|---|
| Screen reader | Every control has `accessibilityLabel` + trait; state announced; logical VoiceOver order | `contentDescription` / Compose `semantics`; role + state; logical TalkBack order |
| Text scaling | Dynamic Type text styles; no fixed point sizes; layout survives the largest accessibility sizes | `sp` for type, never `px`/`dp`; layout survives 200% font scale |
| Touch targets | ≥ 44×44 pt | ≥ 48×48 dp, ≥ 8 dp apart |
| Reduce motion | Honour Reduce Motion (crossfade instead of slide/parallax) | Honour "Remove animations" |
| Contrast | Both appearances (light/dark) and Increase Contrast | Light/dark + high-contrast text |
| Navigation | Tab bar 2–5 sections; nav stack; edge-swipe back never disabled | Nav bar (compact) / rail or drawer (expanded); predictive Back never hijacked |
| Insets | Safe areas: notch, Dynamic Island, home indicator, keyboard | Edge-to-edge with status/nav/cutout/IME insets |
| Platform controls | System switch, picker, sheet, alert, context menu; SF Symbols | Material buttons, FAB (one), snackbar, bottom sheet; Material Symbols |
| Colour | Semantic system colours, not raw hex | Material colour roles; Dynamic Color with static fallback |
| Adaptivity | iPad size classes, Split View, rotation | Window size classes, multi-window, foldable postures |

Severity uses the same rubric as web (`proposal-format.md`). Off-platform controls that still work are P2/P3; ones that break the screen reader, Back, or text scaling are P1/P0.
