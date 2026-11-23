# Project Working Memory

## Goal
Continue improving the School Management System — shipping UI consistency, enrollment/tuition fixes, security hardening, and GitLab deployment.

## Constraints & Preferences
- All `DollarSign` icon usages replaced with custom `PesoSign` SVG component across all frontend pages
- Only SHS (Grade 11, Grade 12) and Bundled Tesda Accredited (1st Year, 2nd Year) grade levels — Grade 7–10 removed entirely
- Graduation year levels: Grade 12 + 2nd Year Bundled Student
- Tours grade levels: `SHS - Grade 11` / `Bundled - 1st Year Tesda Accredited`
- Light-only theme only — all broken dark mode Tailwind variants removed
- Cashier print receipt: `no-print` class moved off modal wrapper to header/footer only; receipt numbers auto-generated as `OR-YYYY-NNNNN` with `localStorage` persistence
- Backend API base URL must not have trailing slash; axios timeout 15s; localStorage calls wrapped in try/catch
- `CORS_ALLOWED_ORIGINS` explicitly whitelisted — no wildcard `*`

## Progress
### Done
- **Tuition edit on the Students page fixed**: the page sends the fee plus the
  running total paid, and the old update wrote that running total into a
  single payment row (a student with two payments of 3,000 showed 12,000 paid
  against a 9,000 entry). The edited row now carries only what the other rows
  of that school year do not cover, the balance follows the year's real total,
  and the payment method keeps its proper label (`Bank Transfer`, not
  `bank_transfer`). The form also prefills the **school year's** paid total
  and the configured academic year, not the calendar.
- **A section decides the placement of its students**: moving a student to
  another section now takes that section's strand and year level with it
  (`_apply_section_placement` + `_sync_grade_label` in `api/views.py`), and
  the transfer is recorded in `section_assigned_by` / `section_assigned_at`.
  The bulk assign does the same - its track/strand only select WHICH students
  move, the target section decides their strand and year level.
- **Section picker**: `frontend/src/components/SectionPicker.jsx` offers the
  school's existing sections (grouped by year level, strand shown) instead
  of a name typed by hand; used on the Students page, in the per-student
  section dialog and in the bulk assign (whose section list is filtered by
  the chosen year level).
- **TuitionPage**: Added alphabetical sort (`filtered.sort((a,b) => a.studentName.localeCompare(b.studentName))`) in `applyFilters`
- **SectionsPage**: Stat cards → colored bg (`rounded-2xl p-4 border border-transparent`), search card → `rounded-2xl border-gray-100`, modal → backdrop blur + sticky header + `rounded-2xl shadow-2xl`; toast notifications added
- **CoursesPage**: Stat cards with colored bg, search/filter card with Reset button, modal updated to ToursPage pattern; toast notifications added
- **TracksPage**: Stat cards, search bar, modal all updated to ToursPage pattern; toast added
- **api.js fixes**: BASE_URL strips trailing slash with `.replace(/\/$/, '')`; `timeout: 15000` on `axios.create`; 401 interceptor no longer calls `/api/auth/logout/` (just clears storage + redirects); network error check `if (!error.response)` at top of response error handler; all `localStorage` calls wrapped in `storage` helper (`get`/`set`/`remove` with try/catch); `configAPI.updateConfig` FormData header set to `undefined` not `'multipart/form-data'`
- **GitLab push**: Remote `https://gitlab.com/D4RK7H3N/SMS.git` added; root `.gitignore` created (excludes node_modules, .venv, dist, .env, __pycache__, etc.); `school_pos/.gitignore` updated to exclude `updates/`; 328 files committed and pushed to `master`
- **Release v1.0.0**: Tagged and pushed; GitLab release created with notes
- **TuitionPage SOA**: View modal replaced with full Statement of Account modal — school header from `SchoolConfigContext`, student info, tuition summary cards (Total/Paid/Balance), **payment history** table fetched from payments API with running balance column, **Print** button with `@media print` CSS (hides all UI except SOA), **Settle Balance** button (sets `amount_paid = total_tuition`), `no-print` class on header/footer
- **Backend enrollment tuition fix**: `TuitionPaymentViewSet.create()` in `api/views.py` now accepts `total_tuition` + `amount_paid` (initial tuition setup mode) in addition to `amount` (normal payment mode). Setting a student's initial tuition no longer fails.
- **`.env` fix**: Was `VITE_API_URL=VITE_API_URL=https://.../api/` (duplicated variable name + trailing path) — corrected to `VITE_API_URL=https://grafting-demote-cruelly.ngrok-free.dev`
- **React Router warnings**: `future={{ v7_startTransition: true, v7_relativeSplatPath: true }}` added to `HashRouter` in `index.jsx`
- **Favicon**: `public/favicon.svg` created (blue square + white "S"), linked in `index.html`
- **Security fixes applied across backend (`school_pos/`):**
  - `api/views.py` — `update_profile` now requires `old_password` to change email; `LoginViewSet` gains `LoginRateThrottle` (10/hour)
  - `students/views.py` — `@login_required` added to `tuition_payment`, `tuition_receipt`, `enroll_student`, `tuition_payment_search`
  - `api/serializers.py` — replaced all `fields = "__all__"` with explicit whitelists; added `date_of_birth = DateField(required=False, allow_null=True, allow_blank=True)` to fix 400 on empty string
  - `settings.py` — `ALLOWED_HOSTS`: removed wildcard `"*"` and subnet wildcard; `REST_FRAMEWORK`: removed `BasicAuthentication`, added `DEFAULT_THROTTLE_CLASSES` + `DEFAULT_THROTTLE_RATES` (`anon: 20/hour`, `user: 1000/hour`); `DEBUG` default changed to `False`
  - CORS: `CORS_ALLOW_ALL_ORIGINS = False`, explicit `CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:8000", "https://grafting-demote-cruelly.ngrok-free.dev"]`
  - `Vary: origin` header confirmed on responses; unauthorized origin (`evil-site.com`) returns no `Access-Control-Allow-Origin` header — CORS blocks it
- **date_of_birth 400 fix**: `StudentsPage.jsx:231` — empty DOB converted to `null` before PUT payload; `serializers.py` — added `allow_blank=True` on DateField for resilience
- **Logout data loss fix**: `AuthContext.jsx:111` — replaced `localStorage.clear()` with targeted `removeItem('authToken')` + `removeItem('user')` — preserves cached config/notification/receipt data
- **Error leakage fix**: `EnrollmentForm.jsx:117` — replaced `setError(err?.response?.data)` (whole backend response) with safe string extraction
- **SettingsPage crash fix**: `SettingsPage.jsx:93` — wrapped `JSON.parse` in try/catch for malformed `schoolConfig`
- **Strand aliases**: `Strand.aliases` field (migration `tracks/0005`) editable
  in Django admin → Tracks → Strands; the importer matches a strand by name,
  code **or** alias, so a programme name can point at a school strand
- **Cluster-strand import rule**: `bulk_upload` no longer overrules the strand
  an admin set on a section; when the sheet names a cluster
  ("Industrial Technologies") the student **inherits the strand of their
  section** (`strands_inherited_from_section` in the response)
- **Import diagnostics**: the response reports `detected_columns`,
  `rows_with_section`, `rows_without_section`, `unmapped_strands`,
  `strands_inherited_from_section`; the Sections page shows them
- **Web deploy**: `npx wrangler deploy` published the current build to Worker
  `sms-3` (`7c400a4d`) — production had been stuck on an old build without the
  Daily Report, graduated students or import panel
- **Self-hosted release feed**: `/releases/<file>` on the Django backend
  (Range support, traversal-safe, `/releases/` exempt from staff auth);
  installers for 1.1.4 + 1.1.5 live in `school_pos/releases/`
- **Releases 1.1.4 - 1.1.9 published** (signed, timestamped). 1.1.5 is the
  first build that reads the self-hosted feed; older clients read the GitHub
  mirror. 1.1.6 fixed the login-screen crash (the shell returns
  `{ id, previousId }`; the pages called `.slice()` on the object) and bundles
  the Inter webfont (`src/assets/fonts`, fetched by `scripts/fetch-fonts.mjs`)
  instead of importing it from fonts.googleapis.com, which the packaged CSP
  blocks. 1.1.7 retries reads after a tunnel blip. 1.1.8 reads the academic
  year from School Config instead of a hardcoded string. 1.1.9 makes the
  updater actually download the update it detects.
- **Nightly off-site backup** → private repo `D4RK7H3N/SMS-Backup` via
  `manage.py backup_to_git`; scheduled task **SMS-Backup** (02:00) runs
  `C:\SMS-Backup\backup.cmd`
- **Tunnel blips**: the Cloudflare tunnel (`sms2-backend`, service
  **Cloudflared**) keeps its process but sometimes loses its edge connection
  for a moment - the edge answers **502** while the backend itself is fine
  (check `http://127.0.0.1:8000` to tell them apart). The frontend repeats
  **reads** once after 1.2 s on 502/503/504; writes are never repeated
  automatically, because a payment whose response was lost must not be
  charged twice.
- **Grade labels**: the importer, the forms and the section grouping all use
  one wording now (`1st Year Bundled` / `2nd Year Bundled`);
  `SectionsPage.normaliseGrade` normalises the year level before grouping, so
  bundled classes land under 1st/2nd Year instead of Other. Shipped in 1.1.12
  (web deployed `fdc56923`, sms3 `3480548`).
- **Sample data**: 720 students imported through the app (files in
  `sample_data/`, generator `school_pos/make_sample_files.py`, remover
  `manage.py clear_sample_students`). Every section filled: 17 SHS x 35 +
  5 bundled x 25. NOTE: there is no `1C` section in the database - only 5
  bundled sections exist.   A verification script briefly deleted the
  user-imported set; restored by re-importing all 22 files (LRN-keyed, so no
  duplicates). The 720-student set is LIVE in the database (user imported
  7 files, all 22 were re-imported after a cleanup slip).
- **Import progress counter** (1.1.13): the bulk import registers under a
  `progress_id` the browser generates and updates done/total per row
  (`_BULK_IMPORT_PROGRESS` in `api/views.py`, polled at
  `/api/students/bulk_upload/progress/?id=` — note the `url_path` makes the
  action nest under bulk_upload). The loading screen polls every 1.5 s and
  shows "Importing N students — X of N done"
  (`LoadingContext.updateGlobalLoading`).
- **E2E suite** (1.1.14): Playwright in `frontend/` (`playwright.config.js`,
  specs in `frontend/e2e/`, run with `powershell -File run-e2e.ps1` or
  `npx playwright test`) — 19 tests against the live web app: auth guard,
  login branding, dashboard, alphabetical roster + search + tabs + row-edit
  section picker, section grouping (no "Other" bucket), import dialogs,
  cashier, tuition, pending (720 balances), revenue, settings, school config,
  and a 720-row import through the real dialog (counter + in-place update).
  Setup injects a real API token for the `e2e-tester` account (superuser,
  kept on purpose; token/password in untracked `e2e/.auth/`). The login
  endpoint is throttled 10/hour, so the setup does NOT post the login form.
  The suite caught a real bug: the students list kept the 15 s axios timeout
  and silently rendered empty rosters on slow links — now 120 s.
- **Payment-flow audit** (`school_pos/test_other_flows.py`, API-level): tours,
  dorm, graduation, GCash references, terminal attribution, delete flows —
  ALL PASS. It found and fixed 4 real bugs: graduation registration 500'd
  (serializer phantom fields `student_lrn`/`enrolled_at`/`lrn`), the
  graduation payment serializer used `payment_method` (model field is
  `method`), dorm assignment rejected every student (gender compared
  'Male'/'Female' against 'M'/'F'), and superuser deletes left stock taken
  (sale) / balances stale (tuition payment). KNOWN LATENT RISK: Sale.
  receipt_number is not unique and is minted client-side per device — two
  terminals can mint the same OR number on the same day (audit ambiguity).
  Dorm payments have no UI collection flow (API only, receipt required).
- **One long list instead of pages** (1.1.16): Students, Pending Payments and
  Tuition now render every row at once (`src/constants/list.js`,
  `ITEMS_PER_PAGE = 2000`), so the page buttons under those tables are gone.
  The data was always fetched in full, so this only changed the DOM.
- **Student list is fast again**: the serializer ran four queries PER student
  (two date aggregates, the tuition sum, a Section lookup for the adviser), so
  720 students cost ~3,000 queries and **7.2 s**. `StudentViewSet.get_queryset`
  now annotates the sum + both dates and `select_related`s the strand, the
  enrolment and the course; the section → adviser map is built once per
  response. **7.2 s → 0.4 s.** `GZipMiddleware` compresses the 924 kB roster to
  57 kB, so it arrives over the school's link in 0.6 s instead of 1.7 s.
  Pages that list students: 12-17 s → 3.5-5 s.
- **Cashier asks for the amount** (1.1.17): the payment dialog has one
  "Amount to collect" field (prefilled with the amount due) instead of
  Full / Half / Other buttons. A partial payment is just a different number.
- **Revenue cards tell the truth** (1.1.17): Total Collected, Tuition, Other
  Payments, Payments Received. "Total Expenses" was hard-coded to 0 and
  "Collection Rate" counted a `status` field the revenue rows do not have, so
  it always read 100 %.
- **The update asks before it installs** (1.1.18): clicking "Check for updates"
  pops the "Update available" dialog **as soon as the version is known** (not
  after the download finishes). The check the user triggers is *interactive*
  (`checkForUpdates(true)` → `ipcMain.handle('check-for-updates', (e,
  interactive)` → `preload.js` passes the flag); the silent background check
  stays quiet, so opening Settings does not throw a dialog at the user.
  "Download and install" → the app restarts as soon as the installer is
  there; "Later" → the update waits for the next quit (`autoInstallOnAppQuit`).
  Only ONE dialog exists - the old "ready to install" dialog is gone.
- **The updater works again** (1.1.17): the self-signed certificate had a
  **folded Subject** — `CN="Dan Aldrin Español, O=USAT College Sagay City, Inc.,
  C=PH"` (one CN holding the whole DN), so electron-updater could never match
  `publisherName` and every update died with *"not signed by the application
  owner"*. The cause was the comma inside "Sagay City, Inc.": the X.509 name
  parser fails on an unquoted comma and folds the whole string into one CN.
  Fix: quote the O value (`O="USAT College Sagay City, Inc."`), which gives real
  CN / O / C parts (`scripts/create-signing-cert.ps1`). A new certificate was
  created, 1.1.16/1.1.17 were re-signed with it, and the installed app
  updated itself 1.1.15 → 1.1.16 with the signature validated.
  **Every staff PC needs the new public certificate trusted** (one command:
  `scripts/install-trusted-cert.ps1` with `C:\certs\sms-signing.cer` as
  admin) — without it the updater still rejects the installer.
- **Dev build vs installed app**: both used the same Electron profile
  (`%APPDATA%\school-management-system`), so the running dev app locked the
  installed app out of its profile — the installed app then could not create
  its disk cache and every window failed with `ERR_FAILED (-2)`. The dev build
  now uses `%TEMP%\sms-dev-profile` (`electron/main.js`).


### In Progress
- **The school's own class lists are imported** (commits `e959a6a`, `a2810d7`,
  `2647c62`, local): the 13 files in `C:\Users\DarkZhen\Documents\System
  Project\USAT\` (`G11 Shs\`, `college bundle\`) → **494 students, every one of
  them in a section** (SHS Grade 11: Amos 13, Daniel 28, David 33, James 28,
  John 31, NOAH 51, Psalms 22, Solomon 26, Thessalonians 24; Bundled 1st Year:
  ATS 1A 52, ATS 1B 47, COE1 32, HRS 1A 51, HRS 1B 56).
  The import rules that make it work:
  - **the FILE NAME names the class** — compared without separators, so
    `ATS 1A` is found in `ATS 1-Anew.xls`, `HRS 1B` in `HRS1B.csv`,
    `COE1` in `COE1.csv`; the section the admin configured gives the row its
    year level (the bundled sheets carry no level column at all)
  - **a blank heading must not shift the columns** — the HRS 1A `.xls` has an
    empty first heading and used to lose its name, LRN and strand
  - the bundled sheets put the qualification in a **Course** column; the SHS
    sheets put it in a **Strand** column — the column decides which one it is
  - a row whose wording names no strand (cluster `Industrial Technologies`,
    or a bundled title) **inherits the strand and the course of its section**
  - `.xls` date cells are read as dates again; `M`/`F`/`Famale` become
    Male/Female
  - **the CSV exports are Windows-1252, not UTF-8** (Excel on Windows) —
    a name like "Broñosa" arrived as "Bro?osa". The files are decoded as
    UTF-8 when they are UTF-8 and as Windows-1252 when they are not
  - "NA" in the LRN cell means "no number yet" → the stable placeholder
  - a student the school lists **twice** (once with the real LRN, once with
    the number Excel rounded away) stays **one** student; the later line wins
  - a number typed as text in Excel keeps a stray quote ("117414100000'") —
    the quote is dropped, the student is matched and not duplicated
  - dry run without touching the roster: `school_pos/test_import_placement.py`
    (uploads every sheet in a transaction that is rolled back)
  - import driver: `frontend/import_usat.cjs` (all 13 files through the API)
  - checkers: `school_pos/show_roster.py`, `find_symbols.py` (broken
    characters), `find_student.py`, `find_quotes.py`
- **151 students carry a placeholder LRN** (0 + 11 digits): the school's
  CSV exports lost the digits to Excel's rounding (`1.17713E+11`) and the ATS
  sheets have no LRN column. The placeholder is stable (name + date of
  birth), so re-importing updates the same student; when the school re-exports
  the LRN column as TEXT the real number replaces the placeholder
  (`placeholders_upgraded` in the import report).
- 5 students have no date of birth (the sheet wrote a future year) and one
  pair are twins with the same name and date of birth (Rose Javier, HRS 1A) —
  both are in the roster as separate students.
- The class list and the roster name the column **"Course"** for a bundled
  class and **"Track / Strand"** for an SHS class (the bundled classes teach
  a course, the SHS classes a strand).
- Desktop release **1.1.19 published** (feed + GitHub mirror, both hold only
  the current version — the old installers are deleted after each publish).
  It carries the Daily Report quantity, the promotion placement, the import
  diagnostics and the **Course** heading of the bundled classes. The web app
  is deployed (Worker `sms-3`) and the frontend is committed to `sms3`
  (`9e08d6d`).
- **Every staff PC must trust the new signing certificate** before it can
  update: run `scripts/install-trusted-cert.ps1` (admin) once per machine
  with `C:\certs\sms-signing.cer`. PCs still on a build from before 1.1.9
  also need one manual install, because their updater never downloaded.

### Blocked
- Railway migration 0004 not yet applied (DB password auth error)
- Existing students on Railway have `custom_tuition_fee = NULL` — SOA shows 0 tuition until re-entered
- PCs still running the pre-1.1.4 build (their `app-update.yml` points at the
  **private** `frontend` repo) cannot self-update - they need one manual
  install of 1.1.9; after that they update from the school own server


## Key Decisions
- SOA replaces the old View modal — adds printable formal statement with payment history + running balance
- Enrollment tuition is set via a two-step flow (student create/patch → `createTuition` with `total_tuition`) — backend now accepts both initial setup and normal payment in the same endpoint
- Security throttling set to 20/hr anonymous, 100/hr authenticated — prevents brute-force on login/change_password without impacting legitimate use
- CORS hardened from `AllowAll` to explicit whitelist after confirming ngrok works with specific origins
- Email change now requires password re-entry — prevents token-only account takeover

## Next Steps
- Have the school re-export the **LRN column as TEXT** (their CSV exports lost
  the digits to Excel's rounding) and upload the files again — the placeholder
  numbers are replaced by the real ones, no duplicates
- Set the **tuition fee** for the 494 imported students (Enroll → Settle
  Balance); the import only carries a fee when the sheet has a Tuition column
  and none of these sheets have one
- Implement the re-enrollment feature (Graduated student re-enrolled into
  2 Year Bundled): enrollment-history model, `Enrolled` status choice,
  `POST /api/students/{id}/re-enroll/` with `select_for_update` and a
  `previous_balance_policy` of BLOCK / WARN_OVERRIDE / CARRY_OVER
- Consider adding `EmailField` validation + confirmation for email changes
- Apply the outstanding Railway migration once the DB connection is fixed
- Re-enter tuition for existing Railway students via Settle Balance

## Storage layout (no card, no subscription)
- **Release feed — self-hosted on the school's own server.**
  `school_pos/releases/` holds `latest.yml`, the installer and the blockmap;
  Django serves them at `/releases/<file>` (`school_pos/releases.py`) with
  real Range support (electron-updater's differential downloads need it).
  Public URL: `https://sms2-api.darkzhub.asia/releases/`.
  - `GET /releases/latest.yml` → no-store (never cached)
  - `GET /releases/<file>` → `public, max-age=31536000, immutable`
  - Path traversal is rejected; only `.exe`, `.blockmap`, `.yml` are served.
  - `/releases/` is exempt from `StaffAuthenticationMiddleware` (the updater
    cannot log in) — the files are public installers, like GitHub Releases.
  - `frontend/scripts/publish-local.mjs` copies the built files there
    (temp name + rename, so a half-written file is never served);
    `npm run release:publish` = local first, then the GitHub mirror.
- **GitHub Releases is only a mirror** for the clients built before the switch
  (they still poll `.../releases/tag/Releases`). `publish-release.mjs` retries
  a dropped upload and uploads the manifest **last**. It takes
  `--owner/--repo/--tag` and creates the release when it does not exist.
- **The update feed must be in a PUBLIC repo.** A client that was built with
  `repo: frontend` can never update: that repo is private and GitHub serves
  release assets of a private repo only to authenticated callers (the app has
  no token) → the check fails with "Could not check for updates". Those PCs
  need one manual install of a current build; after that they update from the
  school's own server.
- **`autoDownload = false` means the updater NEVER downloads.** In
  electron-updater, `checkForUpdates()` only resolves the update info
  (`downloadPromise: this.autoDownload ? this.downloadUpdate(...) : null`),
  so an app that only calls `checkForUpdates()` announces an update that is
  never fetched and nothing is ever installed. `setupAutoUpdate()` must call
  `autoUpdater.downloadUpdate()` explicitly when `update-available` fires.
  Release 1.1.9 fixed this; 1.1.8 and older could detect but never
  download, so they need one manual install of 1.1.9.
- **Off-site backup of the database + uploaded media** → private repo
  `D4RK7H3N/SMS-Backup` (free, no card). Command:
  `manage.py backup_to_git` (`school_config/management/commands/backup_to_git.py`);
  scheduled task **SMS-Backup** runs it nightly at 02:00 via
  `C:\SMS-Backup\backup.cmd`. It dumps the DB to `db.json` (sessions and API
  tokens excluded) and copies `MEDIA_ROOT` into `media/`. Docs:
  `docs/BACKUP.md`.
- R2 is **not** available (no card, no subscription) — do not plan around it.

## Critical Context
- Backend: `school_pos/.venv/Scripts/python.exe manage.py runserver 0.0.0.0:8000`
  (dev) — production runs as the Windows service **DarkZSMS-Backend**
  (waitress on `127.0.0.1:8000`); restart with `Restart-Service -Name
  DarkZSMS-Backend` after any change or migration (a rename without a restart
  caused HTTP 500 on `settlement_context`).
- **SECURITY: never put credentials, API tokens, or passwords in this file.** It is
  tracked in git and pushed to public GitHub/GitLab remotes. Values that used to
  live here (the DB password and a live DRF API token) were disclosed publicly
  and had to be rotated. Keep secrets only in the untracked `school_pos/.env`
  and `.env` files, or a secret manager.
- **Never edit source with PowerShell `Get-Content`/`Set-Content`** — it writes
  a UTF-8 BOM and mangles `₱` into `â‚±`. Use the Edit tool or Node
  (`fs.readFileSync`/`writeFileSync`). `package.json` must stay BOM-free or
  electron-builder fails.
- Production API origin: `https://sms2-api.darkzhub.asia` (behind Cloudflare
  Tunnel -> Django). Frontend: `https://sms.darkzhub.asia`. Public gateway
  Worker: `gw.darkzhub.asia` (Worker `nexus-bridge`).
- Gateway admin endpoints (`/__gateway/*`) require header `X-Gateway-Token`
  (stored as the Worker secret `GATEWAY_TOKEN`); without it they return 404.
- Frontend `.env`: `VITE_API_URL=https://gw.darkzhub.asia`
- Frontend web build is deployed with `npx wrangler deploy` (Worker `sms-3` —
  the `name` in `wrangler.jsonc` must match, otherwise it silently publishes to
  the wrong Worker and production keeps serving a stale build). Git pushes go
  to the `sms3` remote only, never `origin`.
- Build passes: `npx vite build` succeeds with no errors
- GitLab: `https://gitlab.com/D4RK7H3N/SMS` — `master` branch, `v1.0.0` tag

## Strand mapping (USAT College Sagay City, Inc.)
- USAT = "Universal School of Applied Technology" (DepEd school id 406005,
  private SHS, Brgy Poblacion II, Sagay City) — **100% TVL track** in SY
  2024-25 (744 learners), which matches the data: one track (TVL), all 10
  strands under it, every SHS section a TVL specialisation.
- USAT's TESDA-registered programmes (tesda.gov.ph TVI registry): **SMAW NC I/II,
  Computer Systems Servicing NC II, Electronic Products Assembly and Servicing
  NC II, Food and Beverage Services NC II, Housekeeping NC II, Organic
  Agriculture Production NC II** — these map 1:1 onto the school's strands
  (SMAW, ICT-CSS, EPAS, FBS, HK, ACP).
- DepEd's revised TVL curriculum renamed *Computer Systems Servicing* to
  **ICT Programming**, hence the alias `ICT-PROGRAMMING` -> Computer Service
  System.
- **"Industrial Technologies" is a cluster** (welding + electronics + ICT
  programming), so it cannot be aliased to a single school strand. The import
  resolves it from the student's **section** instead — every one of the school's
  SHS sections has exactly one strand set by the admin.
- The school's 10 strands under the 4 official TVL strands:
  Industrial Arts = SMAW, EPAS, Automotive Servicing; ICT = ICT-CSS,
  ICT(.NET), ICT(JAVA); Home Economics = FBS, HK, Bartending;
  Agri-Fishery Arts = ACP. The bundled courses (Automotive Mechanic,
  Computer and Electronics, Hotel and Restaurant Services) are the **2024
  revised TESDA qualification titles** — confirmed the school is on the new
  curriculum.
- **Official titles are now aliases** (`apply_tesda_aliases.py`): the
  registrar's official sheets import with no hand mapping (verified by
  `test_tesda_import.py`, 14 titles, all correct). Courses gained an
  `aliases` field (migration `tracks/0006`); the importer matches courses by
  alias too, and a bundled row takes the **course** while an SHS row takes the
  **strand**.
- Note for SY 2026-2027: DepEd Memorandum No. 012, s. 2026 replaces the
  strand system with the Strengthened SHS Curriculum (two tracks: Academic +
  Technical-Professional, electives instead of strands). The incoming Grade 11
  falls under it; the Grade 12s stay on the old strands.


## Relevant Files
- `frontend/src/pages/TuitionPage.jsx`: alphabetical sort; full SOA modal (school header, payment history table, print CSS, Settle Balance)
- `frontend/src/pages/SectionsPage.jsx`: import dialog (layout example, template, diagnostics panel), grade-grouped listing, Add Section strand/course dropdowns, superadmin delete
- `frontend/src/pages/CashierPage.jsx`: Daily Report button + modal, assessment rows, receipt outstanding balance, walk-in removed
- `frontend/src/pages/StudentsPage.jsx`: All/Active/Graduated tabs, S.Y. filter, pagination fix
- `frontend/src/pages/PendingPaymentsPage.jsx`: Graduated tab, always-visible actions, SOA fixes
- `frontend/src/pages/SchoolConfigPage.jsx`: Advisers card, Daily Report "Checked by"
- `frontend/src/services/api.js`: BASE_URL fallback `''`, `toRelativeApiPath`, `_skipAutoPages`, `page_size:1000`, `adviserAPI`, `cashReportAPI`, bulk-upload timeout 300 s
- `frontend/src/utils/printDocument.js`: `buildDailyCashReportHtml`, `buildRevenueReportHtml`, `buildTerminalReportHtml`, `reportHeader(config,title,subtitle,logo)`
- `frontend/electron/main.js`, `preload.js`: per-installation device id, print-html, auto-update, CSP
- `frontend/scripts/`: `create-signing-cert.ps1`, `build-signed.ps1`, `install-trusted-cert.ps1`, `verify-signature.ps1`, `publish-release.mjs` (cert + password live in `C:\certs\`, outside the repo)
- `frontend/docs/SIGNING.md`, `frontend/docs/RELEASING.md`
- `school_pos/api/views.py` — importer (`bulk_upload`): fuzzy header detection
  (`Section`/`Sec`/`Block`/`Class`, `Track/Strand`), LRN matching, strand match
  by name / code / alias, **the FILE NAME decides the class**
  (`_sections_named_in_file`, separators ignored), the **Course** column of
  the bundled sheets, **cluster strand AND course inherited from the
  section**, the section's admin-set strand is never overwritten, a blank
  heading never shifts the columns, `.xls` date cells are real dates, a
  student listed twice stays one student, response reports
  `detected_columns`, `rows_with_section`, `rows_without_section`,
  `rows_placed_by_file`, `rows_placed_by_strand`, `sections_named_in_file`,
  `unmapped_strands`, `strands_inherited_from_section`, `placeholders_upgraded`
- `school_pos/test_import_placement.py` — dry run of the import (every sheet
  uploaded inside a transaction that is rolled back)
- `school_pos/add_course_aliases.py` — the bundled course aliases the school's
  sheets use ("Hotel and Restaurant Services 1 - A", "COE1", …)
- `school_pos/clear_everything.py`, `school_pos/scan_all_models.py`,
  `school_pos/restore_sections.py`, `school_pos/align_strands_to_files.py`,
  `school_pos/rename_bundled.py` — roster/tooling helpers
- `frontend/import_usat.cjs` — imports every file of the USAT folder through
  the real API and prints the placement report
- `school_pos/tracks/models.py` — `Strand.aliases` (comma separated alternate
  names, editable in Django admin → Tracks → Strands), `Section.adviser`
- `school_pos/school_config/serializers.py` — `SchoolConfigurationUpdateSerializer`
  must include `report_checked_by` (it was missing, so "Checked by" never saved)
- `school_pos/students/models.py` — `status` choices (+Graduated), `graduated_sy`, `school_year`
- `school_pos/school_pos/middleware.py` — `resolve_terminal()` + `X-Device-Previous-Id` terminal migration
- `school_pos/school_pos/permissions.py`, `school_pos/school_pos/throttling.py`, `school_pos/school_pos/pagination.py`
- `docs/superpowers/specs/2026-11-09-daily-cash-report-design.md`, `2026-11-09-section-advisers-design.md`
