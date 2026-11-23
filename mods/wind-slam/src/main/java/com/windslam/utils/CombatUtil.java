package com.windslam.utils;

import com.windslam.config.WindSlamConfig;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.entity.LivingEntity;
import net.minecraft.entity.attribute.EntityAttributes;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.AxeItem;
import net.minecraft.item.ItemStack;
import net.minecraft.item.Items;
import net.minecraft.item.MaceItem;
import net.minecraft.util.math.Vec3d;

public final class CombatUtil {

    private CombatUtil() {
    }

    public static boolean isHoldingMace(ClientPlayerEntity player) {
        return player != null && player.getMainHandStack().getItem() instanceof MaceItem;
    }

    /** True when the 1.9+ attack cooldown bar is fully recharged. */
    public static boolean isAttackReady(PlayerEntity player) {
        return player != null && player.getAttackCooldownProgress(0.5f) >= 1.0f;
    }

    /** Vanilla attack reach attribute (~3.0 by default). */
    public static double getAttackReach(ClientPlayerEntity player) {
        return player.getAttributeValue(EntityAttributes.ENTITY_INTERACTION_RANGE);
    }

    /**
     * Distance from the player's eye point to the target's bounding box
     * (0 while the eye is inside the box) - mirrors how the server's reach check behaves.
     */
    public static double distanceToHitbox(ClientPlayerEntity player, LivingEntity target) {
        Vec3d eye = player.getEyePos();
        net.minecraft.util.math.Box box = target.getBoundingBox();
        double dx = Math.max(Math.max(box.minX - eye.x, 0), eye.x - box.maxX);
        double dy = Math.max(Math.max(box.minY - eye.y, 0), eye.y - box.maxY);
        double dz = Math.max(Math.max(box.minZ - eye.z, 0), eye.z - box.maxZ);
        return Math.sqrt(dx * dx + dy * dy + dz * dz);
    }

    // ------------------------------------------------------------------ items

    /** Spears are the primary stun weapon (lunge/stun); axes are the shield-break backup. */
    public static boolean isSpear(ItemStack stack) {
        if (stack == null || stack.isEmpty()) return false;
        // 1.21.11 spears are plain Item instances — detect by registry id
        return net.minecraft.registry.Registries.ITEM.getId(stack.getItem()).getPath().endsWith("spear");
    }

    /** Axes disable a blocking shield on hit ("stun"). */
    public static boolean isAxe(ItemStack stack) {
        return stack != null && !stack.isEmpty() && stack.getItem() instanceof AxeItem;
    }

    public static boolean isStunWeapon(ItemStack stack) {
        return isSpear(stack) || isAxe(stack);
    }

    /** First hotbar slot (0-8) with the best stun weapon — spear preferred, axe fallback. */
    public static int findStunWeaponSlot(ClientPlayerEntity player) {
        int spear = findInHotbar(player, CombatUtil::isSpear);
        if (spear >= 0) return spear;
        return findInHotbar(player, CombatUtil::isAxe);
    }

    /** Item id check for the wind charge used by the launch. */
    public static boolean isWindCharge(ItemStack stack) {
        return stack != null && stack.getItem() == Items.WIND_CHARGE;
    }

    /** First hotbar slot (0-8) holding wind charges, or -1. */
    public static int findWindChargeSlot(ClientPlayerEntity player) {
        return findInHotbar(player, CombatUtil::isWindCharge);
    }

    /** Total wind charges available on the hotbar (for the HUD). */
    public static int countWindCharges(ClientPlayerEntity player) {
        int total = 0;
        var stacks = player.getInventory().getMainStacks();
        int hotbar = Math.min(9, stacks.size());
        for (int i = 0; i < hotbar; i++) {
            ItemStack s = stacks.get(i);
            if (isWindCharge(s)) total += s.getCount();
        }
        return total;
    }

    private static int findInHotbar(ClientPlayerEntity player, java.util.function.Predicate<ItemStack> test) {
        if (player == null) return -1;
        var stacks = player.getInventory().getMainStacks();
        int hotbar = Math.min(9, stacks.size());
        for (int i = 0; i < hotbar; i++) {
            if (test.test(stacks.get(i))) return i;
        }
        return -1;
    }

    /**
     * True when the player's CURRENT look vector passes through the target's hitbox,
     * i.e. what a real left click would hit. Computed directly (segment vs AABB)
     * instead of MinecraftClient.crosshairTarget, which is a render-time value and
     * can be stale/empty when read from a tick handler.
     */
    public static boolean crosshairOn(net.minecraft.entity.player.PlayerEntity viewer,
                                      LivingEntity target, double reach) {
        if (viewer == null || target == null) return false;
        Vec3d eye = viewer.getEyePos();
        net.minecraft.util.math.Box box = target.getBoundingBox();
        if (box.contains(eye)) return true; // eye already inside (falling onto them)
        Vec3d end = eye.add(viewer.getRotationVec(1.0f).multiply(Math.max(reach, 0.1)));
        return box.raycast(eye, end).isPresent();
    }

    /**
     * Master gate for the mace slam. Returns null if a swing should fire now,
     * otherwise a short reason (for the HUD). The axe stun hit bypasses the
     * fall-distance requirement on purpose - it is a grounded hit.
     */
    public static String slamBlocker(ClientPlayerEntity player, LivingEntity target, WindSlamConfig config) {
        if (target == null || !target.isAlive()) return "no target";
        if (config.onlyWhenHolding && !isHoldingMace(player)) return "no mace";
        double reach = getAttackReach(player) + config.reachTolerance;
        double dist = distanceToHitbox(player, target);
        if (dist > reach) {
            return String.format("out of reach (%.1f/%.1f)", dist, reach);
        }
        if (player.fallDistance < config.minFallDistance) {
            return String.format("falling %.1f/%.1f", player.fallDistance, config.minFallDistance);
        }
        if (config.requireFullCooldown && !isAttackReady(player)) return "cooldown";
        return null;
    }
}
