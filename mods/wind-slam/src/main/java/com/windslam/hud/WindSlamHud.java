package com.windslam.hud;

import com.windslam.WindSlamMod;
import com.windslam.config.WindSlamConfig;
import com.windslam.modules.WindSlamModule;
import com.windslam.utils.CombatUtil;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElement;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.font.TextRenderer;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.client.render.RenderTickCounter;
import net.minecraft.entity.LivingEntity;
import net.minecraft.util.Identifier;

/** Compact live overlay. Only visible while the module is enabled. */
public final class WindSlamHud implements HudElement {

    private static final int MARGIN = 6;
    private static final int BG = 0xB30D1118;
    private static final int ACCENT = 0xFF00E5FF;
    private static final int GREEN = 0xFF2ECC71;
    private static final int RED = 0xFFE74C3C;
    private static final int GRAY = 0xFF9AA3B2;
    private static final int WHITE = 0xFFE8ECF3;

    public static void register() {
        HudElementRegistry.addLast(Identifier.of(WindSlamMod.MOD_ID, "windslam_hud"), new WindSlamHud());
    }

    @Override
    public void render(DrawContext context, RenderTickCounter tickCounter) {
        MinecraftClient client = MinecraftClient.getInstance();
        ClientPlayerEntity player = client.player;
        WindSlamConfig config = WindSlamConfig.get();
        if (player == null || !config.enabled) return;

        TextRenderer tr = client.textRenderer;
        WindSlamModule module = WindSlamMod.getModule();
        LivingEntity target = module == null ? null : module.getCurrentTarget();
        boolean ready = module != null && module.isReadyToAttack();
        String reason = module == null ? null : module.getBlockerReason();

        String statusLine = ready ? "READY"
                : (reason != null ? reason : (module != null ? module.getPhase().name().toLowerCase() : "idle"));
        String targetLine = target == null ? null
                : target.getName().getString() + String.format("  %.1f HP", target.getHealth());
        String chargeLine = config.autoWindLaunch
                ? "charges: " + CombatUtil.countWindCharges(player)
                + (module != null && module.getWindChargeCooldownTicks() > 0
                ? String.format("  (cd %.1fs)", module.getWindChargeCooldownTicks() / 20.0f) : "")
                : null;

        int width = tr.getWidth("WindSlam: " + statusLine);
        if (targetLine != null) width = Math.max(width, tr.getWidth(targetLine));
        if (chargeLine != null) width = Math.max(width, tr.getWidth(chargeLine));
        width += 8;
        int height = 16 + (targetLine != null ? 9 : 0) + (chargeLine != null ? 9 : 0);

        int x = MARGIN;
        int y = MARGIN;
        switch (config.hudCorner) {
            case TOP_RIGHT -> x = context.getScaledWindowWidth() - width - MARGIN;
            case BOTTOM_LEFT -> y = context.getScaledWindowHeight() - height - MARGIN;
            case BOTTOM_RIGHT -> {
                x = context.getScaledWindowWidth() - width - MARGIN;
                y = context.getScaledWindowHeight() - height - MARGIN;
            }
            default -> { /* TOP_LEFT */ }
        }

        context.fill(x, y, x + width, y + height, BG);
        context.fill(x, y, x + width, y + 1, ACCENT);

        int ty = y + 4;
        context.drawText(tr, "WindSlam: " + statusLine, x + 4, ty, ready ? GREEN : RED, false);
        if (targetLine != null) {
            ty += 9;
            context.drawText(tr, targetLine, x + 4, ty, WHITE, false);
        }
        if (chargeLine != null) {
            ty += 9;
            context.drawText(tr, chargeLine, x + 4, ty, GRAY, false);
        }
    }
}
