package com.maceassistant.utils;

import net.minecraft.entity.Entity;
import net.minecraft.util.math.MathHelper;
import net.minecraft.util.math.Vec3d;

public final class RotationUtil {

    private RotationUtil() {
    }

    /** Angle in degrees between the viewer's current look vector and a world-space point. */
    public static double getAngleTo(Entity viewer, Vec3d point) {
        Vec3d look = viewer.getRotationVec(1.0f);
        Vec3d dir = point.subtract(viewer.getEyePos());
        if (dir.lengthSquared() < 1.0E-8) return 0.0;
        double dot = MathHelper.clamp(look.dotProduct(dir.normalize()), -1.0, 1.0);
        return Math.toDegrees(Math.acos(dot));
    }
}
