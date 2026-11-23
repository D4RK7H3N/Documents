package com.windslam.utils;

import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.client.world.ClientWorld;
import net.minecraft.entity.Entity;
import net.minecraft.util.hit.BlockHitResult;
import net.minecraft.util.hit.HitResult;
import net.minecraft.util.math.Vec3d;
import net.minecraft.world.RaycastContext;

public final class EntityUtil {

    private EntityUtil() {
    }

    /** Raycast line-of-sight from the viewer's eyes to the target's eyes or box centre. */
    public static boolean canSee(ClientPlayerEntity from, Entity to, ClientWorld world) {
        if (from == null || to == null || world == null) return false;
        Vec3d eye = from.getEyePos();
        return rayMisses(from, eye, to.getEyePos(), world)
                || rayMisses(from, eye, to.getBoundingBox().getCenter(), world);
    }

    private static boolean rayMisses(Entity viewer, Vec3d start, Vec3d end, ClientWorld world) {
        BlockHitResult result = world.raycast(new RaycastContext(
                start, end,
                RaycastContext.ShapeType.COLLIDER,
                RaycastContext.FluidHandling.NONE,
                viewer));
        return result.getType() == HitResult.Type.MISS;
    }
}
