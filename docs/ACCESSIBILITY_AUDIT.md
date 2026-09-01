# ArchAI Phase 1 Accessibility Audit

**Target:** WCAG 2.2 Level AA

**Scope:** the single-page design studio in its initial state and after concept
generation, including project controls, concept tabs, the 2D plan, exact room
editing, the 3D preview switch, analysis panels, and export controls.

**Audit date:** September 1, 2026

## Methods

- semantic HTML and CSS review against the WCAG 2.2 A/AA success criteria;
- keyboard-path review for bypass navigation, forms, concept switching, room
  selection, movement, exact editing, preview switching, persistence, and export;
- Chromium end-to-end tests with Playwright 1.62.1;
- automated initial-state and generated-state analysis with axe-core 4.13.0 using
  the WCAG 2.0, 2.1, and 2.2 A/AA rule tags;
- minimum-target and focus-obscuring review for the WCAG 2.2 additions.

## Implemented findings

| Area | Phase 1 result |
|---|---|
| Bypass navigation | Skip link moves focus to the main design studio |
| Keyboard access | Native controls, arrow-key room movement, and roving concept tabs |
| Dragging alternative | Exact position and dimension editor provides a no-drag path |
| Focus visibility | High-contrast three-pixel focus indicator and focused SVG-room outline |
| Focus not obscured | Sticky-header scroll padding and per-control scroll margins |
| Target size | Primary interactive controls use at least 40 px visual targets; checkbox targets are enlarged or wrapped by labels |
| Status feedback | Generation, editing, persistence, and errors use visible live regions |
| Motion | Reduced-motion preferences disable authored smooth scrolling and transitions |
| Non-text content | Plan and 3D surfaces expose names, descriptions, and an equivalent 2D route |

## Automated gate

The repeatable audit is implemented in `tests/e2e/archai.spec.js` and runs through
`.github/workflows/quality.yml`. The gate fails when axe reports an A/AA violation
or when the keyboard and primary-workflow assertions fail.

## Boundary

Automated testing cannot prove complete WCAG conformance. A production release
should still be checked with multiple screen readers, browser zoom/reflow, high
contrast modes, voice control, and users with disabilities. This report records a
tested development baseline, not an accessibility certification.

Reference: [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/).
