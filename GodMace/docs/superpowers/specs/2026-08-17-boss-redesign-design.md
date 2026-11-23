# Boss Redesign Design — The Elder Warden & The Crowned Skeleton

**Date:** 2026-08-17
**Status:** Approved
**Scope:** GodMace Paper plugin (`com.freshlol.godmace.GodMacePlugin`)

## Overview

Redesign the two existing treasure-map bosses — the Mega Void Warden and the Mega Bone
Sovereign — into **The Elder Warden** and **The Crowned Skeleton**, giving each real
custom attack patterns, telegraphs, and phase-based behavior instead of being
stat-boosted vanilla mobs.

### Decisions locked during brainstorming

- **Replace** the existing two bosses (not additions, not a duo fight).
- **Custom attack patterns & abilities** are the goal (not just a visual upgrade).
- **Keep the treasure map summon system** (cartographer compass, 500–3000 blocks out).
- **Keep the same legendary drops**: Elder Warden → God Spear, Crowned Skeleton → God Sword.
- **2–3 signature abilities each** plus a real phase change at 50% HP.
- **Implementation approach: scheduler-driven attack loops** (per-boss repeating Bukkit
  task; abilities gated by independent cooldowns; phase 2 shortens cooldowns and unlocks
  an extra ability).

### Out of scope

- Resource pack / Blockbench model work. The plugin keeps referencing
  `WARDEN_MODEL_DATA` (100001) and `SKELETON_MODEL_DATA` (100002); visuals are matched
  to the user's Blockbench designs separately.
- Changes to the God Mace, God Armor, God Spear, God Sword items.
- Changes to the treasure map generation/trade system.

---

## Boss 1: The Elder Warden

**Identity:** An ancient sculk horror that hunts by sound. Slow, relentless,
devastating at close range.

**Visual reference (Blockbench model, out of plugin scope):**

- Massive — same scale as the Crowned Skeleton (2.5)
- Two horn spikes on its body

**Base stats (unchanged from current Mega Void Warden):**

- 5000 HP, scale 2.5, glowing, custom name `§4§l⚠ THE ELDER WARDEN ⚠`
- Boss bar (RED, SEGMENTED_10), treasure-map summon, custom display-entity model
- PDC tag: `boss_tag = "warden"`

### Abilities

Attack loop runs every 1 second (20 ticks). Each ability has an independent cooldown;
the loop picks the first ability off cooldown when a player is in range.

| Ability | Cooldown (P1 / P2) | Effect |
|---|---|---|
| **Sonic Barrage** | 6s / 4s | Roars (telegraph sound + particles), then fires 3 sonic boom projectiles in a spread toward the nearest player within 20 blocks. Each deals ~10 damage + knockback. |
| **Tremor Slam** | 9s / 6s | Telegraphs a 6-block radius with ground particles for ~1s, then slams: players in radius take ~14 damage and are launched upward. |
| **Abyssal Pull** *(Phase 2 only)* | 12s / 8s | Drags all players within 12 blocks toward the warden and blinds them with Darkness for 4s. |

### Phase 2 (HP ≤ 50%)

- Ability cooldowns cut by ~35% (values in table above).
- **Abyssal Pull** unlocks.
- Ambient particles intensify (existing enrage broadcast + purple boss bar retained).

---

## Boss 2: The Crowned Skeleton

**Identity:** A massive skeleton king wielding **two swords** — a relentless melee
duelist who commands his court.

**Base stats & kit:**

- 3000 HP, scale 2.5, glowing, custom name `§8§l☠ THE CROWNED SKELETON ☠`
- Speed II + Strength II potion effects (unchanged)
- Boss bar (WHITE, SEGMENTED_10), treasure-map summon, custom display-entity model
- PDC tag: `boss_tag = "skeleton"`
- **Wields a netherite sword in each hand** — both unbreakable, 0% drop chance,
  cosmetic Sharpness glow
- Keeps royal kit: golden crown helmet, elytra cape, golden boots (all unbreakable,
  0% drop chance)
- **Banner removed** (off-hand is now a sword)

### Abilities

Attack loop runs every 1 second (20 ticks), same cooldown-gating scheme.

| Ability | Cooldown (P1 / P2) | Effect |
|---|---|---|
| **Twin Cleave** | 5s / 3.5s | Dashes at the nearest player within 20 blocks and slashes twice in quick succession (~9 damage each hit, knockback). |
| **Blade Whirlwind** | 10s / 6.5s | Telegraphs with a ring of particles, then spins: all players within 5 blocks (6 in P2) take ~12 damage and are flung outward. |
| **Summon Court** | 14s / 9s | Spawns 3 skeleton guards (100 HP, no drops) around the king. Max 6 alive; guards despawn after 30s or on boss death. |
| **King's Judgment** *(Phase 2 only)* | 12s / 8s | Leaps at the nearest player (telegraphed shadow particles), landing for ~16 damage in a 4-block radius + Slowness II. |

### Phase 2 (HP ≤ 50%)

- Ability cooldowns cut by ~35% (values in table above).
- **King's Judgment** unlocks.
- Blade Whirlwind radius grows from 5 to 6 blocks.

---

## Code Architecture & Shared Infrastructure

All changes live in `GodMacePlugin.java` (single-file plugin).

### New state

```java
// One attack-loop task per boss, started on spawn, cancelled on death/despawn
private final Map<UUID, BukkitTask> bossAttackTasks = new HashMap<>();

// Per-ability cooldown timestamps, keyed by boss UUID, then ability name
private final Map<UUID, Map<String, Long>> abilityCooldowns = new HashMap<>();

// Guard skeletons per boss, for cleanup
private final Map<UUID, Set<UUID>> bossGuards = new HashMap<>();
```

### Attack loop (per boss, every 20 ticks)

1. Check boss is valid; find nearest player within ability range (20–25 blocks).
   No player in range → skip.
2. Check phase (HP ≤ 50% → phase 2, shorter cooldowns).
3. Pick the first ability off cooldown, execute it, stamp its cooldown.

### Cleanup hooks

- `onBossDeath`: cancel attack task, despawn tagged guards, existing boss-bar/display
  cleanup stays.
- `updateBossBars` dead-boss branch: same cleanup (covers non-player kills/despawns).

### Guard skeletons

- Tagged via `bossTagKey = "guard"` — no drops, no boss bar, 100 HP.
- Despawn after 30s (scheduled task) or with the boss.

### Renames

- `spawnWardenBoss` / `spawnSkeletonBoss` keep their names but spawn the redesigned
  bosses (new names, dual swords, attack tasks).
- Broadcast messages updated to the new boss names.

### Boss bar health display

- Boss bar title shows live HP: `<boss name> §8[<current>§7/<max>❤]`, updated every
  second in `updateBossBars` alongside the progress bar.

### Unchanged

- Treasure map system (compass, trade chance, proximity trigger).
- Boss HP pools (5000 / 3000) and scale (2.5).
- God Spear / God Sword drops and broadcast on kill.
- `/getgodmace` commands (`spawnwarden`, `spawnskeleton`, maps, etc.).
- Display-entity model attachment (`attachBossModel`).

---

## Testing

- `/getgodmace spawnwarden` and `/getgodmace spawnskeleton` at player location.
- Verify each ability fires on its cooldown and telegraphs before damage.
- Verify phase 2 triggers at 50% HP: cooldowns shorten, locked abilities unlock.
- Verify guards spawn (max 6), drop nothing, and despawn with the boss or after 30s.
- Verify boss death: attack task cancelled, guards cleaned up, legendary drops,
  boss bar removed, display entity removed.
- Verify treasure-map summon path still works end to end.
