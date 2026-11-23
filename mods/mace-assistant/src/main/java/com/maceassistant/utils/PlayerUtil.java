package com.maceassistant.utils;

import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.client.world.ClientWorld;
import net.minecraft.entity.Entity;
import net.minecraft.util.hit.BlockHitResult;
import net.minecraft.util.hit.HitResult;
import net.minecraft.util.math.Vec3d;
import net.minecraft.world.RaycastContext;

public final class PlayerUtil {

    private PlayerUtil() {
    }

    /**
     * Line-of-sight check from the viewer's eyes. Raycasts to the target's eye line
     * and to the centre of its bounding box - visible if either ray arrives unblocked.
     */
    public static boolean canSee(ClientPlayerEntity from, Entity to, ClientWorld world) {
        if (from == null || to == null || world == null) return false;
        Vec3d eye = from.getEyePos();
        return hasLineOfSight(from, eye, to.getEyePos(), world)
                || hasLineOfSight(from, eye, to.getBoundingBox().getCenter(), world);
    }

    private static boolean hasLineOfSight(Entity viewer, Vec3d start, Vec3d end, ClientWorld world) {
        BlockHitResult result = world.raycast(new RaycastContext(
                start, end,
                RaycastContext.ShapeType.COLLIDER,
                RaycastContext.FluidHandling.NONE,
                viewer));
        return result.getType() == HitResult.Type.MISS;
    }

    public static double getDistanceTo(Entity a, Entity b) {
        if (a == null || b == null) return Double.MAX_VALUE;
        return Math.sqrt(a.squaredDistanceTo(b));
    }
}
