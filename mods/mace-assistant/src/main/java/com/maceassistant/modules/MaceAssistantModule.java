package com.maceassistant.modules;

import com.maceassistant.MaceAssistantMod;
import com.maceassistant.config.MaceAssistantConfig;
import com.maceassistant.gui.MaceAssistantScreen;
import com.maceassistant.utils.MaceUtil;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.entity.LivingEntity;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;
import net.minecraft.util.Hand;

/**
 * Core per-tick logic: pick a target and fire an attack when conditions hold.
 * No aim assist, no camera movement - you look around yourself.
 *
 * Stun Slam: attack a shield-blocking target with an axe to break the shield.
 * The spear is never clicked - its attack is a lunge, which ruins the combo.
 * Leave the axe selected - switching to the mace is always manual.
 */
public class MaceAssistantModule {
    private int attackCooldownTicks = 0; // client-side gate, independent of the weapon cooldown
    private int slotSwitchCooldownTicks = 0; // don't hammer setSelectedSlot every tick
    private final StunSequence stun = new StunSequence();
    private LivingEntity stunTarget;
    private LivingEntity currentTarget;
    private String blockerReason = "no target"; // human-readable reason attacks are paused

    public void onTick(MinecraftClient client) {
        handleKeybinds(client);

        if (attackCooldownTicks > 0) {
            attackCooldownTicks--;
        }
        if (slotSwitchCooldownTicks > 0) {
            slotSwitchCooldownTicks--;
        }

        MaceAssistantConfig config = MaceAssistantConfig.get();
        ClientPlayerEntity player = client.player;

        if (player == null || client.world == null || !config.enabled) {
            currentTarget = null;
            blockerReason = null;
            stun.reset();
            stunTarget = null;
            return;
        }

        // pick the best valid target for this tick
        currentTarget = TargetSelector.selectTarget(player, client.world, config);

        // never attack while a GUI is open - vanilla blocks manual clicks there too
        if (client.currentScreen != null) {
            stun.cancel();
            stunTarget = null;
            blockerReason = "gui open";
            return;
        }
        if (currentTarget == null || client.interactionManager == null) {
            stun.cancel();
            stunTarget = null;
            blockerReason = currentTarget == null ? "no target" : "no interaction manager";
            return;
        }

        blockerReason = tickAttack(client, player, currentTarget, config);
    }

    /**
     * Decides what happens this tick: shield-breaking stun hit, mace smash, or nothing.
     *
     * @return null if an attack was fired, otherwise the reason it didn't
     */
    private String tickAttack(MinecraftClient client, ClientPlayerEntity player,
                              LivingEntity target, MaceAssistantConfig config) {
        long tick = player.age;
        if (!config.stunSlam || stun.expired(tick)) {
            stun.cancel();
            stunTarget = null;
        }
        if (stun.active() && target != stunTarget) {
            stun.cancel();
            stunTarget = null;
            return "stun target changed";
        }
        if (attackCooldownTicks > 0) {
            return "attack delay";
        }

        double dist = MaceUtil.distanceToHitbox(player, target);
        double reach = MaceUtil.getAttackReach(player) + config.reachTolerance;
        if (dist > reach) {
            return String.format("out of reach (%.1f/%.1f)", dist, reach);
        }

        // anti-cheat friendly gate: never swing at what your crosshair isn't on,
        // exactly like a real left click. Covers both stun and mace-slam paths.
        if (config.requireCrosshair && !MaceUtil.crosshairOn(player, target, reach)) {
            return "aim at target";
        }

        // Shield breaker: one axe hit disables the shield. The spear is never
        // clicked (its attack is a lunge) and the mace is never auto-selected.
        // The hit fires the tick after the slot is active - an uncharged axe
        // hit still breaks a shield, so the attack charge is never waited out.
        if (config.stunSlam && (stun.active() || target.isBlocking())) {
            int axeSlot = MaceUtil.findAxeSlot(player);
            if (axeSlot < 0) {
                stun.cancel();
                stunTarget = null;
                return "no axe";
            }
            if (!stun.active() && stun.start(tick)) {
                stunTarget = target;
            }
            if (stun.active()) {
                if (player.getInventory().getSelectedSlot() != axeSlot) {
                    if (slotSwitchCooldownTicks == 0) switchSlot(player, axeSlot);
                    return "switching to axe";
                }
                attack(client, player, target);
                stun.attacked(tick);
                if (!stun.active()) stunTarget = null;
                return "shield break attempted";
            }
        }

        // The server decides whether the axe hit actually disabled the shield.
        // Never auto-select a mace; leave the axe selected after the sequence.

        // -------- normal mace slam --------
        String reason = MaceUtil.attackBlocker(player, target, config);
        if (reason == null) {
            attack(client, player, target);
            return null;
        }
        return reason;
    }

    private void switchSlot(ClientPlayerEntity player, int slot) {
        player.getInventory().setSelectedSlot(slot);
        slotSwitchCooldownTicks = 2;
        attackCooldownTicks = Math.max(attackCooldownTicks, 1);
    }

    /**
     * Fires a normal client attack. The server still enforces reach, cooldown
     * and damage - this is identical to a manual left click, just automated.
     */
    private void attack(MinecraftClient client, ClientPlayerEntity player, LivingEntity target) {
        client.interactionManager.attackEntity(player, target);
        player.swingHand(Hand.MAIN_HAND);
        attackCooldownTicks = Math.max(MaceAssistantConfig.get().attackDelay, 0);
    }

    private void handleKeybinds(MinecraftClient client) {
        MaceAssistantConfig config = MaceAssistantConfig.get();

        // Always drain wasPressed() queues (even while a screen is open) so presses
        // do not buffer up and fire later, but only ACT on them in-game.
        while (MaceAssistantMod.toggleKey.wasPressed()) {
            if (client.currentScreen != null) continue;
            config.enabled = !config.enabled;
            MaceAssistantConfig.save();
            if (client.player != null) {
                client.player.sendMessage(Text.empty()
                        .append(Text.literal("[Mace] ").formatted(Formatting.AQUA))
                        .append(Text.literal(config.enabled ? "enabled" : "disabled")
                                .formatted(config.enabled ? Formatting.GREEN : Formatting.RED)), true);
            }
        }
        while (MaceAssistantMod.openGuiKey.wasPressed()) {
            if (client.currentScreen == null) {
                client.setScreen(new MaceAssistantScreen());
            }
        }
        while (MaceAssistantMod.toggleHudKey.wasPressed()) {
            if (client.currentScreen != null) continue;
            config.showHud = !config.showHud;
            MaceAssistantConfig.save();
            if (client.player != null) {
                client.player.sendMessage(Text.empty()
                        .append(Text.literal("[Mace] ").formatted(Formatting.AQUA))
                        .append(Text.literal("HUD " + (config.showHud ? "visible" : "hidden"))
                                .formatted(Formatting.GRAY)), true);
            }
        }
    }

    public LivingEntity getCurrentTarget() {
        return currentTarget;
    }

    /** True when every attack condition is currently satisfied (for HUD display). */
    public boolean isReadyToAttack() {
        return currentTarget != null && blockerReason == null;
    }

    /** Human-readable reason attacks are blocked right now, or null when ready. */
    public String getBlockerReason() {
        return blockerReason;
    }
}
