package com.windslam.modules;

import com.windslam.WindSlamMod;
import com.windslam.config.WindSlamConfig;
import com.windslam.utils.CombatUtil;
import com.windslam.utils.RotationUtil;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.entity.LivingEntity;
import net.minecraft.item.ItemStack;
import net.minecraft.item.Items;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;
import net.minecraft.util.Hand;

/**
 * Per-tick combo engine:
 * <pre>
 *   IDLE      - target + on ground + charges ready  ->  LAUNCHING
 *   LAUNCHING - one-tick downward pitch glance, timed jump, wind charge throw
 *   AIRBORNE  - stun (axe vs shield) / slam (mace, fall-gated) -> land -> IDLE
 * </pre>
 * Auto-sprint keeps sprint forced on while engaged (incl. mid-air).
 * Everything uses normal interaction packets - visible, server-validated.
 */
public class WindSlamModule {

    public enum Phase { IDLE, LAUNCHING, AIRBORNE }

    private int attackCooldownTicks = 0;
    private int slotSwitchTicks = 0;
    private int windChargeCooldownTicks = 0;
    private long stunSuppressUntil = 0;
    private boolean stunPending = false;   // committed to a stun — follow through even if isBlocking flickers
    private long stunPendingSince = 0;     // when we committed (timeout safety)

    private Phase phase = Phase.IDLE;
    private int launchStep = 0;
    private int burstWaitTicks = 0;    // ticks we've waited for the wind burst after throwing
    private float pitchBackup = 0.0f;
    private long airborneSince = -1L;
    private int sprintGate = 0;        // throttle sprint re-requests to avoid packet spam

    private LivingEntity currentTarget;
    private String blockerReason = null;

    // ------------------------------------------------------------------ tick

    public void onTick(MinecraftClient client) {
        handleKeybinds(client);
        if (attackCooldownTicks > 0) attackCooldownTicks--;
        if (slotSwitchTicks > 0) slotSwitchTicks--;
        if (windChargeCooldownTicks > 0) windChargeCooldownTicks--;

        WindSlamConfig config = WindSlamConfig.get();
        ClientPlayerEntity player = client.player;

        if (player == null || client.world == null || !config.enabled) {
            currentTarget = null;
            blockerReason = null;
            phase = Phase.IDLE;
            launchStep = 0;
            return;
        }

        currentTarget = TargetSelector.selectTarget(player, client.world, config);

        if (client.currentScreen != null) {
            blockerReason = "gui open";
            return;
        }

        // auto-sprint: while a target exists and the player is pressing forward,
        // keep sprint forced on. Throttled (every 3rd tick, and only when the player
        // is actually moving) so point-blank combat doesn't packet-spam.
        if (sprintGate > 0) sprintGate--;
        if (config.autoSprint && currentTarget != null
                && client.options.forwardKey.isPressed() && !player.isSprinting()
                && sprintGate <= 0 && player.getVelocity().horizontalLengthSquared() > 1.0E-4) {
            player.setSprinting(true);
            sprintGate = 3;
        }

        blockerReason = switch (phase) {
            case IDLE -> tickIdle(client, player, config);
            // while mid-launch we do NOT attack or re-trigger anything -
            // keeps close-range engages from all-systems-firing-at-once chaos
            case LAUNCHING -> tickLaunching(client, player, config);
            case AIRBORNE -> tickAirborne(client, player, config);
        };
    }

    // ------------------------------------------------------------------ phases

    private String tickIdle(MinecraftClient client, ClientPlayerEntity player, WindSlamConfig config) {
        if (currentTarget == null) return "no target";

        // a plain fall (ledge etc.) should still slam even if we never launch
        String reason = tryAttack(client, player, config);

        if (!config.autoWindLaunch) return reason;
        if (!player.isOnGround() || player.isClimbing()) return reason;
        if (windChargeCooldownTicks > 0) {
            return String.format("launch cd %.1fs", windChargeCooldownTicks / 20.0f);
        }
        int chargeSlot = CombatUtil.findWindChargeSlot(player);
        if (chargeSlot < 0) return "no wind charge";

        // only launch when the target is in front and in throw range -
        // yeeting yourself up for someone behind you is pointless
        double dist = CombatUtil.distanceToHitbox(player, currentTarget);
        if (dist > config.launchTriggerRange) return reason;
        if (RotationUtil.getAngleTo(player, currentTarget.getBoundingBox().getCenter()) > 70.0) {
            return "face target";
        }
        // vanilla wind charge cooldown also applies (10 ticks + whatever the server enforces)
        if (player.getItemCooldownManager().isCoolingDown(new ItemStack(Items.WIND_CHARGE))) {
            return "charge cd";
        }

        phase = Phase.LAUNCHING;
        launchStep = 0;
        pitchBackup = player.getPitch();
        return "launching";
    }

    private String tickLaunching(MinecraftClient client, ClientPlayerEntity player, WindSlamConfig config) {
        switch (launchStep) {
            case 0 -> {
                int chargeSlot = CombatUtil.findWindChargeSlot(player);
                if (chargeSlot < 0) { abort(client); return "no wind charge"; }
                if (player.getInventory().getSelectedSlot() != chargeSlot) {
                    if (slotSwitchTicks > 0) return "switching";
                    switchSlot(player, chargeSlot);
                    return "switching to charge";
                }
                launchStep = 1;
                return "launching";
            }
            case 1 -> {
                // one visible tick looking at our feet so the throw goes DOWN.
                // NOTE: we do NOT jump here yet - the burst hits 2-4 ticks later
                // and jumping early wastes the jump velocity. We jump AT the burst.
                player.lastPitch = player.getPitch();
                player.setPitch(89.0f);
                client.interactionManager.interactItem(player, Hand.MAIN_HAND);
                windChargeCooldownTicks = Math.max(config.windChargeCooldown, 0);
                launchStep = 2;
                return "thrown!";
            }
            case 2 -> {
                // restore pitch right away so the camera never stays stuck down
                player.setPitch(pitchBackup);
                launchStep = 3;
                burstWaitTicks = 0;
                return "await burst";
            }
            default -> {
                // watch for the burst: the wind charge burst arrives as a big
                // upward velocity bump on the next few ticks. The moment we see
                // it, jump INTO it so jump + burst velocities stack (this is what
                // unlocks the high launch).
                double vy = player.getVelocity().y;
                if (vy > 0.5 || player.fallDistance > 0.1f) {
                    if (config.jumpOnThrow && vy > 0.5) {
                        player.jump();
                    }
                    enterAirborne(client);
                    return "airborne";
                }
                // dud throw, blocked ceiling etc: give up after ~12 ticks
                if (++burstWaitTicks > 12 || !player.isOnGround()) {
                    enterAirborne(client);
                    return "airborne";
                }
                return "await burst";
            }
        }
    }

    private void enterAirborne(MinecraftClient client) {
        launchStep = 0;
        phase = Phase.AIRBORNE;
        airborneSince = client.world.getTime();
    }

    private String tickAirborne(MinecraftClient client, ClientPlayerEntity player, WindSlamConfig config) {
        if (player.isOnGround()) {
            phase = Phase.IDLE;
            return "landed";
        }
        // safety net: give up floating states after 10s (water, levitation, etc.)
        if (client.world.getTime() - airborneSince > 200L) {
            phase = Phase.IDLE;
            return "stale";
        }
        return tryAttack(client, player, config);
    }

    private void abort(MinecraftClient client) {
        phase = Phase.IDLE;
        launchStep = 0;
    }

    // ------------------------------------------------------------------ combat

    /**
     * Stun-first attack decision, then fall-gated mace slam.
     *
     * @return null when an attack fired this tick, otherwise the HUD reason
     */
    private String tryAttack(MinecraftClient client, ClientPlayerEntity player, WindSlamConfig config) {
        LivingEntity target = currentTarget;
        if (target == null) return "no target";
        if (attackCooldownTicks > 0) return null;
        if (client.interactionManager == null) return null;

        double dist = CombatUtil.distanceToHitbox(player, target);
        double reach = CombatUtil.getAttackReach(player) + config.reachTolerance;
        if (dist > reach) {
            return String.format("out of reach (%.1f/%.1f)", dist, reach);
        }

        // anti-cheat friendly gate: crosshair must be on the target's hitbox,
        // exactly like a real left click - covers both stun and slam paths
        if (config.requireCrosshair && !CombatUtil.crosshairOn(player, target, reach)) {
            return "aim at target";
        }

        // -------- stun slam: spear/axe hit breaks an actively-blocking shield --------
        // suppression: after a landed stun the defender visually keeps blocking
        // for a few ticks — without this we hotbar-flicker re-stunning instantly.
        // stunPending: once we commit (see the shield up), we swing even if
        // isBlocking flickers false from sync lag on the next tick.
        boolean stunnedRecently = client.world.getTime() < stunSuppressUntil;

        boolean wantStun = config.stunSlam && target.isBlocking() && !stunnedRecently;
        if (wantStun) {
            stunPending = true;
            stunPendingSince = client.world.getTime();
        }
        if (stunPending && client.world.getTime() - stunPendingSince > 60) {
            stunPending = false; // 3s timeout
        }

        if ((wantStun || (stunPending && config.stunSlam)) && !stunnedRecently) {
            int stunSlot = CombatUtil.findStunWeaponSlot(player);
            if (stunSlot < 0) { stunPending = false; return "no spear/axe"; }
            if (player.getInventory().getSelectedSlot() != stunSlot) {
                if (slotSwitchTicks > 0) return "switching";
                switchSlot(player, stunSlot);
                return "switching to stun";
            }
            if (config.requireFullCooldown && !CombatUtil.isAttackReady(player)) return "cooldown";
            attack(client, player, target);
            stunPending = false;
            stunSuppressUntil = client.world.getTime() + 40; // ~2s, shield is down 5s
            return null;
        }
        if (stunPending && !target.isAlive()) stunPending = false;

        // -------- mace slam --------
        String reason = CombatUtil.slamBlocker(player, target, config);
        if (reason == null) {
            attack(client, player, target);
            return null;
        }
        return reason;
    }

    private void attack(MinecraftClient client, ClientPlayerEntity player, LivingEntity target) {
        client.interactionManager.attackEntity(player, target);
        player.swingHand(Hand.MAIN_HAND);
        attackCooldownTicks = Math.max(WindSlamConfig.get().attackDelay, 0);
    }

    private void switchSlot(ClientPlayerEntity player, int slot) {
        // same packet the number-row keys send; visible in your hotbar
        player.getInventory().setSelectedSlot(slot);
        slotSwitchTicks = 2;
        attackCooldownTicks = Math.max(attackCooldownTicks, 1);
    }

    // ------------------------------------------------------------------ keys

    private void handleKeybinds(MinecraftClient client) {
        WindSlamConfig config = WindSlamConfig.get();
        while (WindSlamMod.toggleKey.wasPressed()) {
            if (client.currentScreen != null) continue;
            config.enabled = !config.enabled;
            WindSlamConfig.save();
            if (client.player != null) {
                client.player.sendMessage(Text.empty()
                        .append(Text.literal("[WindSlam] ").formatted(Formatting.AQUA))
                        .append(Text.literal(config.enabled ? "enabled" : "disabled")
                                .formatted(config.enabled ? Formatting.GREEN : Formatting.RED)), true);
            }
        }
        while (WindSlamMod.openGuiKey.wasPressed()) {
            if (client.currentScreen == null) {
                WindSlamMod.openScreen();
            }
        }
    }

    // ------------------------------------------------------------------ getters

    public LivingEntity getCurrentTarget() {
        return currentTarget;
    }

    public boolean isReadyToAttack() {
        return currentTarget != null && blockerReason == null;
    }

    public String getBlockerReason() {
        return blockerReason;
    }

    public Phase getPhase() {
        return phase;
    }

    public int getWindChargeCooldownTicks() {
        return windChargeCooldownTicks;
    }
}
