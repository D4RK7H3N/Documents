# Shared Workflow

The general cycle used across all projects. Per-project specifics are in
[projects/](projects/), this page covers what is common.

## The Cycle

```
Idea -> Build -> Test -> Commit -> Deploy
```

1. **Idea** - decide what to build; for bigger changes, write a spec first
   (see `docs/superpowers/specs/` under `System Project`).
2. **Build** - implement in small, focused commits (see git conventions).
3. **Test** - run the project's check commands (lint / build / test scripts in
   each project page).
4. **Commit** - commit early and often; see conventions below.
5. **Deploy** - per project (Railway/Docker for school_pos, Netlify for
   portfolio, etc.).

## Git Conventions

- Repos that use git: `ecommerce-app`, `System Project` (school_pos, PORTFOLIO).
- Conventional-ish commit style already in use:
  - `feat:` for new features (e.g. `feat: add edit/delete functionality to TracksPage`)
  - `fix:` for bug fixes (e.g. `fix: replace DamThien332 Fluent fork with official dawid-scripts Fluent`)
  - `security:` for security fixes (e.g. `security: fix P0/P1 issues from CODE_REVIEW.md`)
- Commit messages are descriptive and mention the affected component.
- Never commit secrets: `.env`, `.env.local`, `.env.production` files stay
  gitignored; only commit `.env.example`.

## Project Bootstrapping Checklist

When starting a new project:

1. Create the project folder in `Documents`.
2. If it needs git: `git init`, add a `.gitignore` first, commit early.
3. Include a `README.md` with install/run steps (school_pos and ecommerce-app
  are good templates).
4. Track the project in the [index](../README.md) and add a page under
   `projects/` with its workflow.

## Security Review

For anything that handles money, users, or auth:

- Run a review pass and record it in `CODE_REVIEW.md` (school_pos pattern).
- Fix P0/P1 issues before deploying.
- Keep secrets out of code; load from environment variables.

## Update This Doc

Add or adjust conventions here when they change, then update each project page
only where it differs from this shared workflow.
