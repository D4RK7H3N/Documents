# Design: Workflow Documentation for DarkZhen's Works

Date: 2026-08-13
Status: Approved in conversation (user: "yess")

## Purpose

Catalog all projects under `C:\Users\DarkZhen\Documents` and document the workflow
(how each project is built, run, tested, deployed) plus a shared top-level workflow
page describing the general cycle.

## Location

`C:\Users\DarkZhen\Documents\docs\workflow\`

## Structure

```
docs\workflow\
  README.md                  <- Hub: overview of all projects + status table
  shared-workflow.md         <- General cycle: idea -> build -> test -> commit -> deploy + git conventions
  projects\
    darkzhub.md
    ecommerce-app.md
    fishfinder.md
    fishfinder-display.md
    safeswapph.md
    school-pos.md
    portfolio.md
    mods.md
    arduino.md
```

## Page contents (per project)

- Overview + tech stack
- Status & last activity (from git log where available)
- Per-project workflow (build/run/test/deploy)

## Data source rules

- Fill from actual files (git logs, package.json, READMEs, requirements.txt).
- Mark unknown steps as `[TBD]` for the user to confirm.
- Empty folders (kimi, DARKZHEN) noted as empty, not given pages.

## Hub README contents

- Table of all projects: status, tech, path, link to page.
- Status values: active / archived / idea / empty.
