# UI/UX Redesign — Design Document

Date: 2026-11-07
Status: Approved direction (pending final spec review)
Scope: Full redesign of the web portal and the Flutter student app. Backend API unchanged.

## 1. Goals

The redesign addresses three pains collected during brainstorming:

1. **Looks too plain** — adopt the Stitch "ScholarMetrics" design system as-is (indigo primary,
   green tertiary, blue-tinted surfaces, card-based dashboards).
2. **Hard to use** — a dashboard home, one Gradebook workspace for score entry, consolidated
   admin navigation, and consistent wording.
3. **School branding** — the SNHS logo in the app shell; palette stays the Stitch indigo
   (user decision: "ignore that color" — logo is used as an image, not as a palette source).

## 2. Design language (adopted verbatim from the Stitch export)

Source: `Downloads/stitch_student_grading_system_dashboard/stitch_student_grading_system_dashboard/`

- **Tokens** (from `portal_1/code.html` Tailwind config): `primary #3525CD`,
  `primary-container #4F46E5`, tertiary green `#005338/#006E4B`, error `#BA1A1A`,
  surfaces `#F8F9FF` background, `#FFFFFF` cards, `#E5EEFF` surface-container,
  on-surface `#0B1C30`, on-surface-variant `#464555`, outline `#777587`.
- **Typography**: Plus Jakarta Sans (headlines, 600–700), Inter (body 400–700),
  tabular numerals for scores; uppercase tracking-wider micro-labels.
- **Icons**: Material Symbols Outlined (Google Fonts).
- **Components**: rounded-xl cards with soft shadows; KPI cards (micro-label + big number +
  trend pill + thin progress bar); pill filter rows; pill-style active nav items; dense data
  tables with score cells.
- **Shell**: white sidebar (portal_2 pattern): logo, grouped nav, active item = filled
  indigo pill.

## 3. Screen mapping (Stitch → app)

| Stitch screen | App page | Adaptation |
|---|---|---|
| operations_portal_2 | App shell (all roles) | SNHS logo top; nav grouped Teaching / Manage / Records |
| portal_1 + academic_dashboard_overview | Dashboard | DepEd content: General Average, To Encode, Posted %, Locked quarters; "Needs attention" list with Encode buttons; recent updates feed |
| gradebook_assessment_matrix | Gradebook | Student × assessment score matrix; left rail groups assessments by WW/PT/QA with progress; live quarterly-grade panel; search; keyboard + column paste; single Save-all |
| student_directory_roster_control | Students (admin) | Roster table, create student, CSV import |
| student_academic_profile_performance_detail | Student detail / Class grades | Per-student quarterly/semester/final breakdown |
| examinations_assessment_builder | Assessment builder | Component (WW/PT/QA), quarter, title, HPS |
| curriculum_course_catalog | Subjects, Sections, Assignments | Catalog/list patterns; one "Academics" area instead of three pages |
| institutional_settings_grading_policy | Grading Config | Weights per subject type + transmutation table editor |
| disciplinary_academic_advising_log | Audit Log | Timeline/table with old→new values |
| academic_intelligence_engine | Skipped | Analytics extra, out of thesis scope |

## 4. Terminology standards (fixes "confusing wording")

Banned (Stitch/university jargon): Cohort, At-Risk Scan, GPA, Dean's List, Term, Department,
Semester-B, Surveillance.

Required (DepEd terms): LRN, Section, School Year (S.Y. 2026–2027), Quarter 1–4, Written Work /
Performance Task / Quarterly Assessment, Highest Possible Score, Percentage Score, Initial Grade,
Quarterly Grade, Semester Final Grade, General Average, Transmutation Table, Lock/Unlock quarter.

Nav labels: Dashboard, Gradebook, Students, Academics, Grading Config, Audit Log, User Accounts.

## 5. Explicit exclusions

- **No grade levels anywhere** — the app is section-based; drop any grade-level filters,
  columns, or labels from Stitch screens. Data model already has no grade-level field.
- **No demo/sample content blocks** from the Stitch screens (no "1,420 students",
  "Cohort Fall 2024-B", etc.). Seed data uses realistic Filipino student names, no "Demo" labels.
- No dark mode, no mobile web portal, no parent accounts (future enhancements).

## 6. Information architecture

Web portal (role-filtered sidebar):

- **Teaching** (teacher): Dashboard, Gradebook, My Classes
- **Manage** (admin): Dashboard, Students, User Accounts, Academics (Subjects / Sections /
  Assignments as tabs in one page), Grading Config
- **Records** (admin): Audit Log

Admin sprawl fix: Sections + Subjects + Assignments merge into one "Academics" page with tabs;
everything else keeps its own page but shares the grouped sidebar.

Mobile app (Flutter): same palette and fonts; Material 3 with indigo seed; screens unchanged
(login, change password, grades dashboard with semester toggle, profile) but restyled with
Stitch card patterns, Inter/Plus Jakarta Sans, and the SNHS logo on the login screen.

## 7. Implementation notes

- Web: replace `src/components/ui.jsx` + `Layout.jsx` with a token-based design system;
  port the Stitch Tailwind config (colors, spacing, radii, font families) into the Vite build
  (Tailwind v4 `@theme`); add Google Fonts links; add SNHS logo asset to `web/public/`.
- Rebuild pages in place: Login, ChangePassword, Dashboard (new), Gradebook (replaces
  ClassDetail three-column layout), Students, Academics (merged), Grading Config, Audit Log,
  Users.
- Score grid keeps: keyboard nav, spreadsheet-column paste, blank-vs-zero semantics, invalid
  highlighting, unsaved warning, single save request, post-save grade preview.
- Mobile: restyle existing screens; logo asset added; no logic changes.
- Backend: only `seed_demo` changes (realistic names, no "Demo" labels). No API/model changes.
  All 31 existing tests must keep passing.

## 8. Testing

- `npm run build` must pass after each page conversion.
- Backend test suite (31 tests) unaffected; run after seed_demo change.
- Manual checklist: login → dashboard for both roles; encode flow end-to-end matches the
  document worked example (82.95 → 89); admin pages CRUD; audit entries visible; student
  portal block notice; mobile login + grades render with new theme.
