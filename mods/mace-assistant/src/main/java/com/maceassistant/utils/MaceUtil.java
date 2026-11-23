package com.maceassistant.utils;

import com.maceassistant.config.MaceAssistantConfig;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.entity.LivingEntity;
import net.minecraft.entity.attribute.EntityAttributes;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.AxeItem;
import net.minecraft.item.ItemStack;
import net.minecraft.item.MaceItem;
import net.minecraft.util.math.Vec3d;

public final class MaceUtil {

    private MaceUtil() {
    }

    public static boolean isHoldingMace(ClientPlayerEntity player) {
        return player != null && player.getMainHandStack().getItem() instanceof MaceItem;
    }

    /**
     * Display-only estimate of the mace smash-attack damage multiplier (1.21.x).
     * Smash bonus only kicks in after falling more than ~1.5 blocks; this is an
     * approximation of the vanilla curve, capped so long falls don't print silly numbers.
     */
    public static float getMaceDamageMultiplier(float fallDistance) {
        if (fallDistance < 1.5f) {
            return 1.0f;
        }
        float estimate = 1.0f + (fallDistance - 1.5f) * 0.5f;
        return Math.min(estimate, 8.0f);
    }

    /** True when the 1.9+ attack cooldown bar is fully recharged. */
    public static boolean isAttackReady(PlayerEntity player) {
        return player != null && player.getAttackCooldownProgress(0.5f) >= 1.0f;
    }

    /**
     * Vanilla attack reach (the {@code entity_interaction_range} attribute, ~3.0 by
     * default). The server silently drops attack packets beyond this, so we gate on it.
     */
    public static double getAttackReach(ClientPlayerEntity player) {
        return player.getAttributeValue(EntityAttributes.ENTITY_INTERACTION_RANGE);
    }

    /**
     * Distance from the player's eye point to the target's BOUNDING BOX (not its centre).
     * This matches how the server's reach check behaves while you are falling onto a
     * target: getting closer vertically doesn't inflate the distance inside the box.
     */
    public static double distanceToHitbox(ClientPlayerEntity player, LivingEntity target) {
        Vec3d eye = player.getEyePos();
        // 1.21.11: Box.squaredDistanceTo was removed; point-to-AABB distance by hand.
        // (0 while the eye is inside the box, so falling onto a target reads as "close")
        net.minecraft.util.math.Box box = target.getBoundingBox();
        double dx = Math.max(Math.max(box.minX - eye.x, 0), eye.x - box.maxX);
        double dy = Math.max(Math.max(box.minY - eye.y, 0), eye.y - box.maxY);
        double dz = Math.max(Math.max(box.minZ - eye.z, 0), eye.z - box.maxZ);
        return Math.sqrt(dx * dx + dy * dy + dz * dz);
    }

    // ------------------------------------------------------------------ weapons

    /** Spears are the first attack in the spear-then-axe stun sequence. */
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

    public static int findSpearSlot(ClientPlayerEntity player) {
        return findInHotbar(player, MaceUtil::isSpear);
    }

    public static int findAxeSlot(ClientPlayerEntity player) {
        return findInHotbar(player, MaceUtil::isAxe);
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
     * i.e. what a real left click would hit. Computed directly here (segment vs AABB)
     * instead of relying on MinecraftClient.crosshairTarget, which is a render-time
     * value that can be stale/empty when read from a tick handler.
     */
    public static boolean crosshairOn(net.minecraft.entity.player.PlayerEntity viewer,
                                      LivingEntity target, double reach) {
        if (viewer == null || target == null) return false;
        Vec3d eye = viewer.getEyePos();
        net.minecraft.util.math.Box box = target.getBoundingBox();
        if (box.contains(eye)) return true; // eye already inside (e.g. falling onto them)
        Vec3d end = eye.add(viewer.getRotationVec(1.0f).multiply(Math.max(reach, 0.1)));
        return box.raycast(eye, end).isPresent();
    }

    /**
     * Master gate for firing an automatic MACE attack. Returns null when the attack
     * may fire, or a short human-readable reason it is blocked. Conditions:
     * <ul>
     *   <li>target exists and is alive</li>
     *   <li>holding a mace (if {@code onlyWhenHolding})</li>
     *   <li>within vanilla interaction range (server rejects anything further)</li>
     *   <li>falling at least {@code minFallDistance} (mace smash bonus window)</li>
     *   <li>weapon cooldown fully charged (if {@code requireFullCooldown})</li>
     * </ul>
     * Note: the shield-breaking stun hit is handled separately in the module and
     * intentionally bypasses the fall-distance requirement.
     */
    public static String attackBlocker(ClientPlayerEntity player, LivingEntity target, MaceAssistantConfig config) {
        if (player == null || target == null || !target.isAlive()) {
            return "no target";
        }
        if (config.onlyWhenHolding && !isHoldingMace(player)) {
            return "no mace";
        }
        double reach = getAttackReach(player) + config.reachTolerance;
        // +reachTolerance covers client/server position desync at the edge of range:
        // we ATTEMPT the hit, the server validates it and may still legitimately miss it
        double dist = distanceToHitbox(player, target);
        if (dist > reach) {
            return String.format("out of reach (%.1f/%.1f)", dist, reach);
        }
        if (player.fallDistance < config.minFallDistance) {
            return String.format("falling %.1f/%.1f", player.fallDistance, config.minFallDistance);
        }
        if (config.requireFullCooldown && !isAttackReady(player)) {
            return "cooldown";
        }
        return null;
    }
}
