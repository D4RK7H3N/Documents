# Professional UI Refresh — Design Specification

Date: 2026-11-19
Status: Approved design, pending written spec review
Scope: Visual and usability refresh of the React teacher/admin portal and Flutter student app.

## 1. Relationship to the existing redesign

This specification supersedes the indigo visual language and the mobile-web exclusion in
`2026-11-07-ui-redesign-design.md`. Its established DepEd terminology, screen inventory, grade-entry
behavior, role-based workflows, and backend boundaries remain in force.

The refresh uses a unified design-system approach across web and Flutter. It does not introduce a
second visual direction for administrators, teachers, or students.

## 2. Goals

1. Make the interface feel lighter, more professional, and more cohesive through a powder-blue,
   white, and dark-slate visual language.
2. Improve hierarchy, spacing, component consistency, responsive navigation, mobile data access,
   and touch usability.
3. Preserve all existing workflows, APIs, authentication behavior, routes, grade calculations, and
   Provider/AuthContext data flow.
4. Reuse the existing Tailwind and Material 3 component foundations rather than adding a UI library.

## 3. Non-goals

- No new screens, user roles, API endpoints, data models, or academic features.
- No changes to score-entry semantics, quarter locking, password policies, or permissions.
- No new font dependencies, dark mode, decorative gradients, or screen-by-screen bespoke themes.
- No functional router or backend bug fixes unless a UI adjustment directly requires one.

## 4. Visual language

### 4.1 Palette

| Role | Color | Usage |
|---|---|---|
| Page background | `#EAF3F8` | Pale powder-blue app and page background |
| Raised surface | `#FFFFFF` | Cards, dialogs, menus, and primary content surfaces |
| Subtle surface | `#F4F8FB` | Inputs, grouped content, and subdued panels |
| Navigation | `#1F2A37` | Desktop sidebar, structured navigation, and dark headers |
| Primary action | `#263C52` | Primary buttons with white text |
| Primary hover | `#1B2E40` | Hover/pressed dark-slate action state |
| Powder-blue accent | `#C9E2F0` | Selected fills, subtle highlights, and branded accents |
| Selected surface | `#D9EBF5` | Active navigation and selected controls with dark text |
| Primary text | `#17232D` | Headings, body copy, and important values |
| Secondary text | `#566573` | Supporting copy and metadata |
| Border | `#D2E0E8` | Cards, fields, dividers, and table boundaries |
| Focus/link | `#3A6880` | Visible focus rings and accessible text links |
| Success | `#167154` | Positive academic and system states only |
| Warning | `#8A5A00` | Warning states only |
| Error | `#B42318` | Errors and destructive states only |

Powder blue is not used behind white body text. Dark slate carries primary actions and navigation so
contrast does not depend on the light accent color. Status colors remain distinct from brand accents.

### 4.2 Typography and iconography

- Retain Inter for body copy, controls, and data, and Plus Jakarta Sans for headings.
- Use tabular numerals for grades, scores, percentages, and other comparative values.
- Strengthen hierarchy through heading size/weight, readable body text, and quieter metadata rather
  than excessive uppercase labels.
- Retain Material Symbols Outlined on web and Material icons in Flutter.
- Use the school logo consistently without deriving additional colors or decorative gradients.

### 4.3 Spacing, shape, and elevation

- Use the existing spacing foundations, correcting inconsistent gaps at shared-component level.
- Use moderate corner radii: approximately 8px for controls and 10–12px for cards and dialogs.
- Prefer thin blue-gray borders and flat surfaces; reserve subtle shadows for raised navigation,
  menus, dialogs, and important cards.
- Keep desktop data density while providing at least 44px touch targets for primary mobile controls.

## 5. Component and platform design

### 5.1 React teacher/admin portal

- Centralize palette, typography, spacing, radii, and focus styling in the Tailwind theme and global
  styles.
- Apply the visual system through the existing shared headers, cards, KPI cards, buttons, fields,
  notices, tables, empty states, dialogs, toasts, and navigation components.
- Restyle the desktop sidebar and header without changing role-filtered destinations.
- Limit page-specific edits to layout, responsive behavior, alignment, and state presentation.
- Preserve existing form behavior, gradebook keyboard interaction, dialogs, and route structure.

### 5.2 Flutter student app

- Centralize the equivalent palette through Material 3 `ColorScheme`, text, app-bar, card, button,
  input, dialog, snack-bar, and navigation themes.
- Restyle login, forced password change, grades dashboard, semester selection, and profile using the
  same visual roles as the web portal.
- Retain bottom navigation, existing screen composition, and Provider state flow.
- Reuse shared logo and component patterns rather than creating unrelated screen-local themes.

### 5.3 Shared states and accessibility

- Standardize loading, empty, error, success, disabled, hover, pressed, selected, and focus states.
- Preserve visible keyboard focus and accessible names for icon-only controls.
- Meet WCAG AA contrast for normal text and essential control states.
- Keep error messages adjacent to the relevant form or content region and avoid relying on color
  alone to communicate academic status.
- Menus and drawers must support keyboard operation, Escape dismissal, and sensible focus return.

## 6. Responsive behavior

### 6.1 Teacher/admin portal

- Desktop retains the fixed sidebar and dense data presentation.
- Below the desktop breakpoint, replace the long horizontal navigation strip with a compact header
  and menu drawer containing the same role-filtered destinations and logout action.
- On narrow screens, action-heavy student and user records use responsive record cards so names,
  key metadata, statuses, and actions remain visible without hidden horizontal controls.
- Wide academic matrices may remain tabular with horizontal scrolling, sticky learner identifiers,
  and a visible scroll cue. This exception is for comparison-heavy data, not ordinary CRUD tables.
- Forms stack cleanly, primary actions become full-width where beneficial, and filters wrap without
  clipping or overlapping.

### 6.2 Flutter student app

- Retain bottom navigation and existing workflows at all supported widths.
- Keep login, password-change, grades, and profile content scrollable with safe-area padding.
- Semester controls, cards, actions, and grade rows must remain readable without overflow at 320px.
- Preserve readable typography and practical touch targets rather than shrinking content to fit.

## 7. Data flow and error handling

The refresh is presentation-only. Existing API requests, token/session handling, AuthContext,
Provider state, query parameters, and grade transformations remain unchanged. The mobile API client
continues to declare JSON request bodies as `application/json`.

Existing asynchronous states receive consistent visual treatment. A styling change must not swallow
errors, replace server validation with invented client rules, or introduce fallback data. Empty and
error states remain distinguishable from loading states.

## 8. Validation and acceptance criteria

### 8.1 Web

- Run the production build successfully.
- Review login and core teacher/admin routes at 1440px desktop, 768px tablet, and 390px mobile.
- Verify drawer keyboard/touch behavior, role-filtered navigation, forms, dialogs, tables/record
  cards, wide-matrix scrolling, and loading/error/empty states.
- Confirm no document-level horizontal overflow, clipped primary actions, new console errors, or
  unreadable contrast in the audited views.
- Recheck existing grade-entry and administrative workflows for regressions.

### 8.2 Flutter

- Analyze changed application source and run relevant widget tests.
- Verify login, password change, grades, semester switching, profile, loading/error/empty states,
  and bottom navigation at 390px and 320px widths.
- Review the actual rendered interface on the connected Android phone using the deployed backend.
- Confirm no layout overflow, obscured controls, unreadable text, or regression to session and API
  behavior.

### 8.3 Completion standard

The refresh is complete when the approved palette and shared states are applied consistently across
both platforms, mobile navigation and record actions are directly usable, all existing workflows
remain intact, and the validation above has been performed with any pre-existing failures reported
separately from new regressions.
