package com.maceassistant.modules;

import com.maceassistant.config.MaceAssistantConfig;
import com.maceassistant.utils.PlayerUtil;
import com.maceassistant.utils.RotationUtil;
import net.minecraft.client.network.AbstractClientPlayerEntity;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.client.world.ClientWorld;
import net.minecraft.entity.Entity;
import net.minecraft.entity.LivingEntity;
import net.minecraft.registry.Registries;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Runs once per client tick. Single pass over players (and mobs, if enabled)
 * with early-continue filters, then one small sort of the survivors.
 */
public final class TargetSelector {

    private TargetSelector() {
    }

    public static LivingEntity selectTarget(ClientPlayerEntity player, ClientWorld world, MaceAssistantConfig config) {
        List<LivingEntity> candidates = new ArrayList<>();
        double rangeSq = (double) config.targetRange * config.targetRange;

        // ---- players ----
        for (AbstractClientPlayerEntity candidate : world.getPlayers()) {
            if (candidate == player) continue;                                    // never ourselves
            if (!keepEntity(player, candidate, world, config, rangeSq)) continue;

            String name = candidate.getName().getString();
            // blacklist always wins over whitelist
            if (MaceAssistantConfig.containsName(config.blacklist, name)) continue;
            if (config.useWhitelist && !MaceAssistantConfig.containsName(config.targetWhitelist, name)) continue;

            candidates.add(candidate);
        }

        // ---- mobs (opt-in) ----
        if (config.targetMobs) {
            for (Entity entity : world.getEntities()) {
                if (!(entity instanceof LivingEntity living)) continue;
                if (entity instanceof AbstractClientPlayerEntity) continue;       // players handled above
                if (!keepEntity(player, living, world, config, rangeSq)) continue;
                // mob whitelist: empty list = every mob is fair game
                if (!config.mobWhitelist.isEmpty()
                        && !mobAllowed(config.mobWhitelist, living)) continue;
                candidates.add(living);
            }
        }

        if (candidates.isEmpty()) return null;

        Comparator<LivingEntity> comparator = switch (config.sortMode) {
            case CLOSEST -> Comparator.comparingDouble(player::squaredDistanceTo);
            case LOWEST_HEALTH -> Comparator.comparingDouble(LivingEntity::getHealth);
            case HIGHEST_HEALTH -> Comparator.comparingDouble(LivingEntity::getHealth).reversed();
            // FOV: whoever is closest to the current crosshair wins
            case FOV -> Comparator.comparingDouble(
                    e -> RotationUtil.getAngleTo(player, e.getBoundingBox().getCenter()));
        };

        candidates.sort(comparator);
        return candidates.get(0);
    }

    /** Shared filters for players and mobs. */
    private static boolean keepEntity(ClientPlayerEntity player, LivingEntity candidate, ClientWorld world,
                                      MaceAssistantConfig config, double rangeSq) {
        if (candidate.isDead() || candidate.getHealth() <= 0.0f) return false;    // corpses out
        if (!config.targetInvisible && candidate.isInvisible()) return false;     // invis filter
        if (player.squaredDistanceTo(candidate) > rangeSq) return false;         // range gate (cheap)
        // most expensive check last: the LOS raycast
        return !config.requireLineOfSight || PlayerUtil.canSee(player, candidate, world);
    }

    private static boolean mobAllowed(List<String> whitelist, LivingEntity mob) {
        String path = Registries.ENTITY_TYPE.getId(mob.getType()).getPath(); // e.g. "zombie"
        for (String allowed : whitelist) {
            String a = allowed.contains(":") ? allowed.substring(allowed.indexOf(':') + 1) : allowed;
            if (a.equalsIgnoreCase(path)) return true;
        }
        return false;
    }
}
