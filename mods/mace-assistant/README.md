# Mace Combat Assistant

A client-side **Fabric** mod for **Minecraft 1.21.11** that assists with mace PvP
mechanics: fall-distance-gated auto attacks, shield-breaking axe swaps
("stun slam"), smart target selection, a settings GUI and a minimal live HUD.

Designed for **private servers / personal testing**. Everything the mod does is
client-visible and server-honest: no packet spoofing, no camera teleporting, no
rotation hiding, and all attacks go through the normal interaction path (the
server still enforces reach, cooldowns and damage).

---

## Features

### Combat core
- **Fall-distance gated attacks** — a mace swing only fires while you are
  falling at least the configured distance (the mace smash bonus window).
  Normal flat-ground jumps peak at ~1.25 blocks, so a threshold of **1.5+**
  means attacks only happen off real falls / wind-charge launches.
- **Full attack cooldown support** — optionally waits for a 100% charged swing.
- **Vanilla reach enforcement** — targets are only attacked within the actual
  `entity_interaction_range`, so the server never silently drops your swings.
- **No aim assist, no auto-movement** — you look and move; the mod only swings.

### Stun Slam (shield break)
- When a target is **actively blocking with a shield** (right-click held) and
  you have **both a spear and an axe** on your hotbar, the mod:
  1. auto-selects the spear and attacks once its cooldown is ready,
  2. auto-selects the axe and attacks once its cooldown is ready to attempt
     the shield break (the server determines success),
  3. leaves the axe selected afterwards; switching to the mace is always manual.
- Both attacks respect reach, aim and line-of-sight settings, with no fall-distance
  requirement. Losing the target or opening a GUI cancels the sequence.
- There is no axe-only fallback: a missing weapon is reported in the HUD.
- Can be disabled entirely in the GUI.

### Target selection
- Scans **players**, and optionally **mobs**, within a configurable range.
- Sort modes: **Closest**, **Lowest HP**, **Highest HP**, **FOV**
  (nearest to your crosshair).
- Filters: dead/0 HP entities, invisible entities, line of sight
  (block-raycast from your eyes), max range.
- **Player whitelist** (only these players are targeted) and **blacklist**
  (never targeted; always wins over the whitelist).
- **Mob whitelist** — entity ids like `zombie` or `minecraft:skeleton`;
  empty list = all mobs allowed.

### GUI
- Open with **RIGHT SHIFT**; the game keeps running (screen never pauses).
- Tabbed panel: **General / Targets / Mobs / Whitelist**.
- Sliders with live values, toggles, cycle buttons — every change is saved
  to disk instantly.
- **Online player side panel** (right side, auto-hidden if the window is too
  narrow, e.g. fullscreen at GUI scale 4):
  - green `[W]` = whitelisted, red `[B]` = blacklisted, gray = neutral
  - **left click** row = toggle whitelist, **right click** = toggle blacklist
  - HP shown next to visible players.
- Panel shrinks to fit small windows / high GUI scales automatically.

### HUD
- Two compact lines: status (`READY` or the exact reason it is blocked, e.g.
  `falling 0.4/1.5`, `out of reach (4.2/3.0)`, `no mace`, `cooldown`) plus the
  current target with HP.
- Corner configurable (all four). Only visible while the module is enabled.

### Keybinds
| Key | Action |
|---|---|
| `V` | Toggle module on/off (feedback in the action bar) |
| `RIGHT SHIFT` | Open settings GUI |

Both are rebindable in Options → Controls.

---

## Requirements

| Component | Version |
|---|---|
| Minecraft | **1.21.11** |
| Fabric Loader | ≥ 0.19.0 |
| Fabric API | any 1.21.11 build, e.g. 0.141.6 |
| Java | 21+ |

## Installation

1. Install Fabric Loader for Minecraft 1.21.11.
2. Put **Fabric API** and this mod's jar into your `mods` folder.
3. Launch, press **V** to enable, **RIGHT SHIFT** to configure.

## Building from source

Requires Java 21+ and Gradle 9.x (a wrapper is included):

```bash
./gradlew build
# => build/libs/mace-assistant-<version>.jar
```

Optional IntelliJ/Eclipse setup, run configs, etc. behave like any stock
Fabric Loom project (`./gradlew genSources`, `./gradlew runClient`).

## Configuration

Stored at `.minecraft/config/mace_assistant.json` (auto-saved on every GUI
change; unknown/extra keys are ignored when loading).

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | master switch (V key) |
| `onlyWhenHolding` | bool | `true` | only attack while holding a mace |
| `stunSlam` | bool | `true` | spear attack, then axe shield-break attempt |
| `targetRange` | float | `6.0` | scan radius in blocks |
| `sortMode` | enum | `CLOSEST` | `CLOSEST` / `LOWEST_HEALTH` / `HIGHEST_HEALTH` / `FOV` |
| `minFallDistance` | float | `1.5` | minimum fall before a mace swing fires |
| `requireFullCooldown` | bool | `true` | wait for 100% attack charge |
| `attackDelay` | int | `2` | minimum ticks between swings |
| `requireLineOfSight` | bool | `true` | raycast block check |
| `targetInvisible` | bool | `false` | allow invisible targets |
| `targetWhitelist` | string[] | `[]` | only these players (when `useWhitelist`) |
| `blacklist` | string[] | `[]` | never hit these players |
| `useWhitelist` | bool | `false` | enable player whitelist mode |
| `targetMobs` | bool | `false` | allow mob targeting |
| `mobWhitelist` | string[] | `[]` | mob ids, empty = all mobs |
| `hudCorner` | enum | `TOP_LEFT` | HUD placement |

## Project structure

```
src/main/java/com/maceassistant/
├── MaceAssistantMod.java      entrypoint, keybinds, registrations
├── config/MaceAssistantConfig.java
├── modules/
│   ├── MaceAssistantModule.java   tick loop, stun-slam flow, attacks
│   └── TargetSelector.java        filtering + sorting
├── gui/
│   ├── MaceAssistantScreen.java   4-tab settings screen + side panel
│   └── TargetListWidget.java      scrollable editable name lists
├── hud/MaceHud.java               compact overlay
└── utils/
    ├── MaceUtil.java              weapon/reach/cooldown/blocker logic
    ├── PlayerUtil.java            LOS raycast, distances
    └── RotationUtil.java          crosshair-angle helper (FOV sort)
```

## Disclaimer

Use responsibly: the mod is honest client-side automation intended for private
servers and testing. Check the rules of any server you play on — automation
of combat may be disallowed on public servers regardless of how it is built.

## License

MIT
