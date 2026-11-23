package com.maceassistant.hud;

import com.maceassistant.MaceAssistantMod;
import com.maceassistant.config.MaceAssistantConfig;
import com.maceassistant.modules.MaceAssistantModule;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElement;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.font.TextRenderer;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.client.render.RenderTickCounter;
import net.minecraft.entity.LivingEntity;
import net.minecraft.util.Identifier;

/**
 * Compact in-game overlay: one status line (READY or the reason it is blocked)
 * plus the current target. Registered via Fabric's HudElementRegistry.
 * Only drawn while the module is enabled.
 */
public final class MaceHud implements HudElement {

    private static final int MARGIN = 6;

    // palette
    private static final int BG = 0xB30D1118;
    private static final int ACCENT = 0xFF00E5FF;
    private static final int GREEN = 0xFF2ECC71;
    private static final int RED = 0xFFE74C3C;
    private static final int WHITE = 0xFFE8ECF3;

    public static void register() {
        HudElementRegistry.addLast(Identifier.of(MaceAssistantMod.MOD_ID, "mace_hud"), new MaceHud());
    }

    @Override
    public void render(DrawContext context, RenderTickCounter tickCounter) {
        MinecraftClient client = MinecraftClient.getInstance();
        ClientPlayerEntity player = client.player;
        MaceAssistantConfig config = MaceAssistantConfig.get();
        if (player == null || !config.enabled || !config.showHud) return;

        TextRenderer tr = client.textRenderer;
        MaceAssistantModule module = MaceAssistantMod.getModule();
        LivingEntity target = module == null ? null : module.getCurrentTarget();
        boolean ready = module != null && module.isReadyToAttack();
        String reason = module == null ? null : module.getBlockerReason();

        // line 1: status
        String statusLine = ready ? "Mace: READY"
                : "Mace: " + (reason == null ? "WAITING" : reason);
        // line 2: target (only when there is one)
        String targetLine = target == null ? null
                : target.getName().getString() + String.format("  %.1f HP", target.getHealth());

        int width = tr.getWidth(statusLine);
        if (targetLine != null) {
            width = Math.max(width, tr.getWidth(targetLine));
        }
        width += 8; // horizontal padding
        int height = targetLine == null ? 16 : 25;

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

        context.drawText(tr, statusLine, x + 4, y + 4, ready ? GREEN : RED, false);
        if (targetLine != null) {
            context.drawText(tr, targetLine, x + 4, y + 13, WHITE, false);
        }
    }
}
