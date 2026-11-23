# PORTFOLIO

## Overview

Personal single-page portfolio for **DarkZhen / Dan Aldrin** - self-taught
full-stack developer & systems engineer from Sagay City, Philippines. SPA with
3D (React Three Fiber) hero + draggable 3D project panels (gated by device
capability), a built-in AI assistant ("Zhen"), command palette, easter eggs,
and a 2D starfield fallback. Project showcase embeds live demos via iframe
(DarkZ Management System, its landing page, ClickBound Commerce).

**Path:** `C:\Users\DarkZhen\Documents\System Project\PORTFOLIO` (git repo,
origin GitLab `D4RK7H3N/portfolio-of-my-own`)

**Tech stack:** Vite 6, React 18, React Three Fiber 8 + drei + uikit,
Three.js, Framer Motion, MUI (declared, unused - candidate for pruning),
Tailwind-style custom CSS (`src/gl/glass.css`)

## Status

**Active** - no recent commits in the System Project log for this folder;
last iteration was the starfield background + AI assistant work.

## Sections (single page, smooth-scroll anchors)

| Section | Content |
|---|---|
| Home | Circular profile photo (glowing gradient ring), glitch-text name, typed subtitle, magnetic CTAs, scroll indicator |
| About | Bio - self-taught, ALS -> Grade 12 ICT (USAT College Sagay City), built DarkZ Management System |
| Skills | 8 animated bars: React/Next 90, REST/GraphQL 88, Node 85, PG/MySQL 85, Python/Django 82, Git/CI-CD 80, Electron 78, UI/UX 72 |
| Showcase | 3D draggable panels (capable devices) + live iframe cards: DarkZ Management System (`sms.darkzhub.asia`), landing page (`dashboard.darkzhub.asia`), ClickBound Commerce (in development) |
| Experience | Timeline story (self-teaching journey, tribute to late father) |
| Contact | Email, GitLab, location, GitHub glass cards |

## Architecture

- **`src/three/`**
  - `SceneHeroBackdrop.jsx` - fixed fullscreen Canvas: 9 glass slabs (transmission
    0.4) in a circle, Float drift, parallax camera, fog + colored lights;
    respects prefers-reduced-motion, aria-hidden.
  - `SceneShowcasePanels.jsx` - 620px Canvas: one uikit panel per project
    (badge, LIVE dot, tech chips, Launch Full Demo / View Source buttons),
    DragControls (y-clamped ±1.6, relax animation), `noGlyphs()` strips
    em-dashes (uikit font limitation).
  - `use3DCapable.js` - WebGL test + device score (hardwareConcurrency x
    deviceMemory, coarse-pointer penalty) requiring >= 16; cached globally.
  - `SpatialErrorBoundary.jsx` - falls back to 2D starfield on 3D failure.
  - Both scenes are React.lazy + Suspense.
- **Components:** InteractiveCursor, CommandPalette (⌘K), KonamiEasterEgg
  (Matrix rain), TextScramble/Typewriter/GlitchText, MagneticTilt, ScrollProgress
  + BackToTop, ParticleNetwork (always-on canvas), StarfieldBackground (fallback),
  BrowserMockup + LiveDemoModal (reload/open-in-new-tab/close).
- **AI assistant (`AiChat/`):** floating chat bubble -> glass drawer; proxy
  `POST /v1/chat` (OpenAI-style) with 120s timeout; offline demo mode when
  URL unset; `ground-data.js` compiles portfolio facts into the system prompt;
  persona "Zhen" must never reveal the model/vendor.

## AI backend (Cloudflare Worker)

`System Project\ai-assistant\worker\worker.js` proxies chat to NVIDIA's
OpenAI-compatible endpoint (`integrate.api.nvidia.com/v1/chat/completions`,
default model `minimaxai/minimax-m3`). API key held as Worker secret
(`NVIDIA_API_KEY`), client system prompts stripped, messages clamped to 20,
optional KV rate limiting (30/min, disabled by default).

## Workflow

1. **Install:** `npm install`
2. **Env:** `VITE_AI_PROXY_URL` in `.env.local` / `.env.production` (both
   committed except *.local); code also has a hardcoded fallback proxy URL so
   the AI chat works when unset.
3. **Dev:** `npm run dev`
4. **Build:** `npm run build` (root-absolute `/assets/...` paths - no `base`
   config; built output verified: main bundle + lazy 3D chunks + uikit font
   worker).
5. **Preview:** `npm run preview`
6. **Deploy:** manual/out-of-band (no netlify.toml, no CI config in repo);
   dist is gitignored. `[TBD - exact publish steps]`

### Test checklist

- 3D gate: check `use3DCapable` (score >= 16) - most phones/weak laptops get
  the starfield fallback; drag panels on capable desktops.
- AI chat online vs offline mode; typing dots; retry on error.
- Command palette, Konami code, cursor, scroll progress, reduced-motion.
- Stale copy check: `index.html` meta description still says "creator of
  SchoolPOS" while branding is "DarkZ Management System" (known issue).

## Design history

Specs in `docs/superpowers/specs/` (2026-08-08): spatial glass portfolio
design, AI assistant design. Sibling `System Project\Netlify` is the separate
SMS landing page (Vite 8 + lucide-react, netlify.toml, GitLab D4RK7H3N/SMS) -
not this project.
