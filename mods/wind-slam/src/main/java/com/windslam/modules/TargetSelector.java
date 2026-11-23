package com.windslam.modules;

import com.windslam.config.WindSlamConfig;
import com.windslam.utils.EntityUtil;
import com.windslam.utils.RotationUtil;
import net.minecraft.client.network.AbstractClientPlayerEntity;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.client.world.ClientWorld;
import net.minecraft.entity.Entity;
import net.minecraft.entity.LivingEntity;
import net.minecraft.registry.Registries;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Per-tick target sweep: cheap filters first, LOS raycast last, then sort. */
public final class TargetSelector {

    private TargetSelector() {
    }

    public static LivingEntity selectTarget(ClientPlayerEntity player, ClientWorld world, WindSlamConfig config) {
        List<LivingEntity> candidates = new ArrayList<>();
        double rangeSq = (double) config.targetRange * config.targetRange;

        // players
        for (AbstractClientPlayerEntity candidate : world.getPlayers()) {
            if (candidate == player) continue;
            if (!keep(player, candidate, world, config, rangeSq)) continue;

            String name = candidate.getName().getString();
            if (WindSlamConfig.containsName(config.blacklist, name)) continue;   // blacklist wins
            if (config.useWhitelist && !WindSlamConfig.containsName(config.targetWhitelist, name)) continue;

            candidates.add(candidate);
        }

        // mobs (opt-in)
        if (config.targetMobs) {
            for (Entity entity : world.getEntities()) {
                if (!(entity instanceof LivingEntity living)) continue;
                if (entity instanceof AbstractClientPlayerEntity) continue;
                if (!keep(player, living, world, config, rangeSq)) continue;
                if (!config.mobWhitelist.isEmpty() && !mobAllowed(config.mobWhitelist, living)) continue;
                candidates.add(living);
            }
        }

        if (candidates.isEmpty()) return null;

        Comparator<LivingEntity> comparator = switch (config.sortMode) {
            case CLOSEST -> Comparator.comparingDouble(player::squaredDistanceTo);
            case LOWEST_HEALTH -> Comparator.comparingDouble(LivingEntity::getHealth);
            case HIGHEST_HEALTH -> Comparator.comparingDouble(LivingEntity::getHealth).reversed();
            case FOV -> Comparator.comparingDouble(
                    e -> RotationUtil.getAngleTo(player, e.getBoundingBox().getCenter()));
        };
        candidates.sort(comparator);
        return candidates.get(0);
    }

    private static boolean keep(ClientPlayerEntity player, LivingEntity candidate, ClientWorld world,
                                WindSlamConfig config, double rangeSq) {
        if (candidate.isDead() || candidate.getHealth() <= 0.0f) return false;
        if (!config.targetInvisible && candidate.isInvisible()) return false;
        if (player.squaredDistanceTo(candidate) > rangeSq) return false;
        return !config.requireLineOfSight || EntityUtil.canSee(player, candidate, world);
    }

    private static boolean mobAllowed(List<String> whitelist, LivingEntity mob) {
        String path = Registries.ENTITY_TYPE.getId(mob.getType()).getPath();
        for (String allowed : whitelist) {
            String a = allowed.contains(":") ? allowed.substring(allowed.indexOf(':') + 1) : allowed;
            if (a.equalsIgnoreCase(path)) return true;
        }
        return false;
    }
}
