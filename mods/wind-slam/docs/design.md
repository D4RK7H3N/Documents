# WindSlam — Design

Client-side Fabric mod for Minecraft 1.21.11 that automates the mace PvP combo:
sprint approach -> wind-charge self-launch -> (optional axe shield-break) -> mace slam.
Honest by design: real item-use and slot packets only, no packet spoofing, no hidden
rotations; camera moves are visible one-tick glances; the server validates everything.

## State machine (WindSlamModule)

- IDLE: waiting on conditions (target, on ground, wind charge available, cooldowns).
- LAUNCHING: wind charge thrown this tick (pitch-glance at feet, jump timed with
  the throw). Transitions to AIRBORNE when fallDistance > 0.
- AIRBORNE: attack decisions live here — stun path first (blocking target + axe),
  then mace slam gated on fall distance / cooldown / reach (+tolerance).
  Returns to IDLE on landing.

## Flow details

1. Target via shared TargetSelector (players + optional mobs, whitelist/blacklist).
2. Auto-sprint: while enabled and a target exists and W is pressed, force sprint
   (visible, server-visible).
3. Launch trigger: on ground, target within `launchTriggerRange`, wind charge on
   hotbar, wind charge not on cooldown (vanilla cooldown manager AND custom
   `windChargeCooldown` ticks to respect servers with slower rules), pitch glance
   down (~89 deg) for one tick while jumping + using the item. Pitch restores
   the next tick.
4. Stun slam: blocking target + axe in hotbar -> select axe, hit when cooldown
   ready, 40-tick suppression after a landed stun to avoid flicker.
5. Slam: fall distance >= `minFallDistance`, full cooldown (optional), eye-to-box
   distance <= interaction reach + `reachTolerance`.

## Config (JSON, Gson, auto-save)

enabled, onlyWhenHolding(mace), stunSlam, autoWindLaunch, autoSprint,
jumpOnThrow, launchTriggerRange, windChargeCooldown (ticks, default 20),
targetRange, reachTolerance, sortMode, minFallDistance, requireFullCooldown,
attackDelay, requireLineOfSight, targetInvisible, targetWhitelist, blacklist,
useWhitelist, targetMobs, mobWhitelist, hudCorner.

## GUI (Right Shift)

5 tabs: General, Launch, Targets, Mobs, Whitelist. Same scaffolding as
mace-assistant (dark panel, cyan accent, side player panel, auto-shrink layout).
Keys: V toggles, Right Shift opens GUI (rebindable; if mace-assistant is also
installed, rebind one of them).

## HUD

Two lines: `WindSlam: <state or reason>` + target line. Blocker states include:
launch cooldown seconds, axe-switch states, fall/reach/cooldown blockers.

## Known limits (documented in README)

- Launch height is bounded by vanilla physics; a well-timed jump assists it.
- Wind charges only come from the hotbar; empty = no launch.
- Server cooldowns always win over client settings.
