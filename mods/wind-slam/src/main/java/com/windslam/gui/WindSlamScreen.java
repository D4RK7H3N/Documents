package com.windslam.gui;

import com.windslam.WindSlamMod;
import com.windslam.config.WindSlamConfig;
import com.windslam.modules.WindSlamModule;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.font.TextRenderer;
import net.minecraft.client.gui.Click;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.gui.widget.SliderWidget;
import net.minecraft.client.gui.widget.TextFieldWidget;
import net.minecraft.client.network.AbstractClientPlayerEntity;
import net.minecraft.entity.Entity;
import net.minecraft.entity.LivingEntity;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.registry.Registries;
import net.minecraft.text.Text;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.function.Consumer;
import java.util.function.Supplier;

/**
 * WindSlam settings screen. Never pauses the game; shrinks to fit small windows
 * and high GUI scales; saves every change instantly.
 */
public class WindSlamScreen extends Screen {

    private static final int PANEL_W = 320;
    private static final int PANEL_H = 400;
    private static final int SIDE_W = 150;
    private static final int SIDE_GAP = 6;
    private static final int HEADER_H = 22;
    private static final int ONLINE_ROW_H = 11;
    private static final int STRIP_H = 46;

    private static final String[] TABS = {"General", "Launch", "Targets", "Mobs", "Whitelist"};

    private static final int BG = 0xE6111520;
    private static final int BG_SIDE = 0xE60E1219;
    private static final int ACCENT = 0xFF00E5FF;
    private static final int TEXT = 0xFFDDE3EE;
    private static final int DIM = 0xFF8892A6;
    private static final int GREEN = 0xFF2ECC71;
    private static final int RED = 0xFFE74C3C;

    private int currentTab = 0;
    private int panelX;
    private int panelY;
    private int panelH;
    private int sideX;
    private int sideW;
    private boolean sideVisible;

    private TextFieldWidget nameField;
    private TextFieldWidget mobField;
    private TargetListWidget whitelistList;
    private TargetListWidget blacklistList;
    private TargetListWidget mobList;

    private final List<PlayerEntity> onlinePlayers = new ArrayList<>();

    /** Nearby mob-type ids shown in the side panel on the Mobs tab ("one-click add to list"). */
    private final List<String> nearbyMobIds = new ArrayList<>();
    private int nearbyMobsY = -1;

    public WindSlamScreen() {
        super(Text.literal("WindSlam"));
    }

    @Override
    public boolean shouldPause() {
        return false;
    }

    @Override
    public void renderBackground(DrawContext context, int mouseX, int mouseY, float deltaTicks) {
        // keep the world visible behind the panel
    }

    @Override
    protected void init() {
        panelH = Math.min(PANEL_H, this.height - 12);

        sideW = SIDE_W;
        sideVisible = this.width >= PANEL_W + SIDE_GAP + 100;
        if (sideVisible) {
            sideW = Math.min(SIDE_W, this.width - PANEL_W - SIDE_GAP - 12);
        }

        int totalWidth = PANEL_W + (sideVisible ? SIDE_GAP + sideW : 0);
        panelX = (this.width - totalWidth) / 2;
        panelY = (this.height - panelH) / 2;
        sideX = panelX + PANEL_W + SIDE_GAP;

        buildWidgets();
    }

    private void buildWidgets() {
        this.clearChildren();
        nameField = null;
        mobField = null;
        whitelistList = null;
        blacklistList = null;
        mobList = null;

        int tabW = (PANEL_W - 12 - (TABS.length - 1) * 4) / TABS.length;
        int tabsX = panelX + 6;
        int tabY = panelY + HEADER_H + 4;
        for (int i = 0; i < TABS.length; i++) {
            final int index = i;
            ButtonWidget tab = ButtonWidget.builder(Text.literal(TABS[i]), button -> {
                        currentTab = index;
                        this.clearAndInit();
                    })
                    .dimensions(tabsX + i * (tabW + 4), tabY, tabW, 18)
                    .build();
            tab.active = currentTab != index;
            addDrawableChild(tab);
        }

        WindSlamConfig config = WindSlamConfig.get();
        int x = panelX + 12;
        int w = PANEL_W - 24;
        int y = panelY + HEADER_H + 28;

        switch (currentTab) {
            case 0 -> { // GENERAL
                addDrawableChild(toggle(x, y, w, "Enabled", () -> config.enabled, v -> config.enabled = v)); y += 26;
                addDrawableChild(toggle(x, y, w, "Stun Slam (spear/axe)", () -> config.stunSlam, v -> config.stunSlam = v)); y += 26;
                addDrawableChild(toggle(x, y, w, "Auto Sprint", () -> config.autoSprint, v -> config.autoSprint = v)); y += 26;
                addDrawableChild(new FloatSlider(x, y, w, "Min Fall Distance", 0.0, 10.0, 0.5,
                        config.minFallDistance, v -> config.minFallDistance = v.floatValue(), "%.1f")); y += 26;
                addDrawableChild(new FloatSlider(x, y, w, "Attack Delay (ticks)", 0.0, 20.0, 1.0,
                        config.attackDelay, v -> config.attackDelay = v.intValue(), "%.0f")); y += 26;
                addDrawableChild(cycle(x, y, w,
                        () -> "Sort Mode: " + config.sortMode,
                        () -> config.sortMode = config.sortMode.next())); y += 26;
                addDrawableChild(cycle(x, y, w,
                        () -> "HUD Corner: " + config.hudCorner,
                        () -> config.hudCorner = config.hudCorner.next()));
            }
            case 1 -> { // LAUNCH
                addDrawableChild(toggle(x, y, w, "Auto Wind Launch", () -> config.autoWindLaunch, v -> config.autoWindLaunch = v)); y += 26;
                addDrawableChild(toggle(x, y, w, "Jump On Throw", () -> config.jumpOnThrow, v -> config.jumpOnThrow = v)); y += 26;
                addDrawableChild(new FloatSlider(x, y, w, "Launch Trigger Range", 1.0, 12.0, 0.5,
                        config.launchTriggerRange, v -> config.launchTriggerRange = v.floatValue(), "%.1f")); y += 26;
                addDrawableChild(new FloatSlider(x, y, w, "Wind Charge Cooldown", 5.0, 60.0, 5.0,
                        config.windChargeCooldown, v -> config.windChargeCooldown = v.intValue(),
                        "%.0f ticks")); // your server's 1s rule = 20 ticks here
            }
            case 2 -> { // TARGETS
                addDrawableChild(new FloatSlider(x, y, w, "Target Range (scan)", 1.0, 20.0, 0.5,
                        config.targetRange, v -> config.targetRange = v.floatValue(), "%.1f")); y += 26;
                addDrawableChild(new FloatSlider(x, y, w, "Reach Tolerance", 0.0, 1.0, 0.05,
                        config.reachTolerance, v -> config.reachTolerance = v.floatValue(), "%.2f")); y += 26;
                addDrawableChild(toggle(x, y, w, "Target Invisible", () -> config.targetInvisible, v -> config.targetInvisible = v)); y += 26;
                addDrawableChild(toggle(x, y, w, "Whitelist Mode", () -> config.useWhitelist, v -> config.useWhitelist = v)); y += 26;
                addDrawableChild(toggle(x, y, w, "Require Full Cooldown",
                        () -> config.requireFullCooldown, v -> config.requireFullCooldown = v)); y += 26;
                addDrawableChild(toggle(x, y, w, "Require Line of Sight",
                        () -> config.requireLineOfSight, v -> config.requireLineOfSight = v)); y += 26;
                addDrawableChild(toggle(x, y, w, "Require Crosshair",
                        () -> config.requireCrosshair, v -> config.requireCrosshair = v));
            }
            case 3 -> buildMobsTab(x, y, w);
            case 4 -> buildWhitelistTab(x, y, w);
        }
    }

    private void buildMobsTab(int x, int y, int w) {
        WindSlamConfig config = WindSlamConfig.get();

        addDrawableChild(toggle(x, y, w, "Target Mobs", () -> config.targetMobs, v -> config.targetMobs = v));
        y += 28;

        mobField = new TextFieldWidget(this.textRenderer, x, y, 228, 18, Text.literal("Mob id"));
        mobField.setMaxLength(32);
        mobField.setPlaceholder(Text.literal("mob id, e.g. zombie"));
        addDrawableChild(mobField);

        addDrawableChild(ButtonWidget.builder(Text.literal("Add"), button -> {
                    if (WindSlamConfig.addName(config.mobWhitelist, mobField.getText())) {
                        WindSlamConfig.save();
                        mobField.setText("");
                    }
                })
                .dimensions(x + 234, y, 62, 18)
                .build());

        int bottom = panelY + panelH - STRIP_H - 8;
        int listTop = y + 26;
        int listH = Math.max(30, bottom - listTop - 26);
        mobList = new TargetListWidget(this.textRenderer, x, listTop, w, listH,
                config.mobWhitelist, WindSlamConfig::save);

        int clearY = listTop + listH + 8;
        addDrawableChild(ButtonWidget.builder(Text.literal("Clear Mob List"), button -> {
                    config.mobWhitelist.clear();
                    WindSlamConfig.save();
                })
                .dimensions(x, clearY, 110, 18)
                .build());
    }

    private void buildWhitelistTab(int x, int y, int w) {
        WindSlamConfig config = WindSlamConfig.get();

        nameField = new TextFieldWidget(this.textRenderer, x, y, 176, 18, Text.literal("Player name"));
        nameField.setMaxLength(16);
        nameField.setPlaceholder(Text.literal("Player name"));
        addDrawableChild(nameField);

        addDrawableChild(ButtonWidget.builder(Text.literal("+ Whitelist"), button -> {
                    if (WindSlamConfig.addName(config.targetWhitelist, nameField.getText())) {
                        WindSlamConfig.save();
                        nameField.setText("");
                    }
                })
                .dimensions(x + 184, y, 54, 18)
                .build());
        addDrawableChild(ButtonWidget.builder(Text.literal("+ Blacklist"), button -> {
                    if (WindSlamConfig.addName(config.blacklist, nameField.getText())) {
                        WindSlamConfig.save();
                        nameField.setText("");
                    }
                })
                .dimensions(x + 240, y, 56, 18)
                .build());

        int bottom = panelY + panelH - STRIP_H - 8;
        int listsTop = y + 30;
        int clearBtnH = 18;
        int avail = bottom - listsTop - 12 - clearBtnH - 2 * 12;
        int listH = Math.max(30, (avail - 8) / 2);

        whitelistList = new TargetListWidget(this.textRenderer, x, listsTop, w, listH,
                config.targetWhitelist, WindSlamConfig::save);
        int blacklistY = listsTop + listH + 12;
        blacklistList = new TargetListWidget(this.textRenderer, x, blacklistY, w, listH,
                config.blacklist, WindSlamConfig::save);

        int clearY = blacklistY + listH + 6;
        addDrawableChild(ButtonWidget.builder(Text.literal("Clear Whitelist"), button -> {
                    config.targetWhitelist.clear();
                    WindSlamConfig.save();
                })
                .dimensions(x, clearY, 90, clearBtnH)
                .build());
        addDrawableChild(ButtonWidget.builder(Text.literal("Clear Blacklist"), button -> {
                    config.blacklist.clear();
                    WindSlamConfig.save();
                })
                .dimensions(x + 96, clearY, 90, clearBtnH)
                .build());
    }

    // ------------------------------------------------------------------ widgets

    private ButtonWidget toggle(int x, int y, int w, String label,
                                Supplier<Boolean> getter, Consumer<Boolean> setter) {
        ButtonWidget button = ButtonWidget.builder(Text.empty(), b -> {
                    setter.accept(!getter.get());
                    b.setMessage(Text.literal(label + ": " + (getter.get() ? "ON" : "OFF")));
                    WindSlamConfig.save();
                })
                .dimensions(x, y, w, 20)
                .build();
        button.setMessage(Text.literal(label + ": " + (getter.get() ? "ON" : "OFF")));
        return button;
    }

    private ButtonWidget cycle(int x, int y, int w, Supplier<String> label, Runnable action) {
        ButtonWidget button = ButtonWidget.builder(Text.empty(), b -> {
                    action.run();
                    b.setMessage(Text.literal(label.get()));
                    WindSlamConfig.save();
                })
                .dimensions(x, y, w, 20)
                .build();
        button.setMessage(Text.literal(label.get()));
        return button;
    }

    private static final class FloatSlider extends SliderWidget {
        private final String label;
        private final double min;
        private final double max;
        private final double step;
        private final Consumer<Double> setter;
        private final String format;

        FloatSlider(int x, int y, int w, String label, double min, double max, double step,
                    double current, Consumer<Double> setter, String format) {
            super(x, y, w, 20, Text.empty(), bound01((current - min) / (max - min)));
            this.label = label;
            this.min = min;
            this.max = max;
            this.step = step;
            this.setter = setter;
            this.format = format;
            updateMessage();
        }

        private double mapped() {
            double v = min + this.value * (max - min);
            return Math.round(v / step) * step;
        }

        @Override
        protected void updateMessage() {
            setMessage(Text.literal(label + ": " + String.format(format, mapped())));
        }

        @Override
        protected void applyValue() {
            setter.accept(mapped());
            WindSlamConfig.save();
        }

        private static double bound01(double v) {
            return Math.max(0.0, Math.min(1.0, v));
        }
    }

    // ------------------------------------------------------------------ render

    @Override
    public void render(DrawContext context, int mouseX, int mouseY, float deltaTicks) {
        drawPanels(context);
        super.render(context, mouseX, mouseY, deltaTicks);
        drawDynamicInfo(context);
        if (sideVisible) {
            drawSidePanel(context, mouseX, mouseY);
        }
        if (whitelistList != null) whitelistList.render(context, mouseX, mouseY);
        if (blacklistList != null) blacklistList.render(context, mouseX, mouseY);
        if (mobList != null) mobList.render(context, mouseX, mouseY);
    }

    private void drawPanels(DrawContext context) {
        context.fill(panelX, panelY, panelX + PANEL_W, panelY + panelH, BG);
        context.fill(panelX, panelY, panelX + PANEL_W, panelY + 2, ACCENT);

        int tabW = (PANEL_W - 12 - (TABS.length - 1) * 4) / TABS.length;
        int tabsX = panelX + 6;
        int underlineY = panelY + HEADER_H + 4 + 18;
        context.fill(tabsX + currentTab * (tabW + 4), underlineY,
                tabsX + currentTab * (tabW + 4) + tabW, underlineY + 2, ACCENT);

        context.fill(panelX, panelY + panelH - STRIP_H, panelX + PANEL_W, panelY + panelH - STRIP_H + 1, 0xFF2A3345);

        if (sideVisible) {
            context.fill(sideX, panelY, sideX + sideW, panelY + panelH, BG_SIDE);
            context.fill(sideX, panelY, sideX + sideW, panelY + 1, ACCENT);
        }

        TextRenderer tr = this.textRenderer;
        context.drawText(tr, "WindSlam", panelX + 8, panelY + 8, TEXT, false);
        boolean enabled = WindSlamConfig.get().enabled;
        String status = enabled ? "ACTIVE" : "INACTIVE";
        context.drawText(tr, status, panelX + PANEL_W - tr.getWidth(status) - 8, panelY + 8,
                enabled ? GREEN : RED, false);

        if (sideVisible) {
            context.drawText(tr, "Online Players", sideX + 6, panelY + 8, TEXT, false);
        }
    }

    private void drawDynamicInfo(DrawContext context) {
        TextRenderer tr = this.textRenderer;
        MinecraftClient client = MinecraftClient.getInstance();
        WindSlamModule module = WindSlamMod.getModule();
        LivingEntity target = module == null ? null : module.getCurrentTarget();

        int y = panelY + panelH - STRIP_H + 8;
        if (target != null && target.isAlive()) {
            String line = "Target: " + target.getName().getString()
                    + String.format(" (%.1f HP)", target.getHealth());
            context.drawText(tr, trim(tr, line, PANEL_W - 90), panelX + 10, y, TEXT, false);
        } else {
            context.drawText(tr, "Target: none", panelX + 10, y, DIM, false);
        }

        if (client.player != null) {
            String fall = String.format("F: %.2f", client.player.fallDistance);
            context.drawText(tr, fall, panelX + PANEL_W - tr.getWidth(fall) - 10, y, DIM, false);

            float cd = Math.max(0.0f, Math.min(1.0f, client.player.getAttackCooldownProgress(0.5f)));
            int barX = panelX + 10;
            int barY = y + 14;
            int barW = 150;
            context.fill(barX, barY, barX + barW, barY + 6, 0xFF252C3A);
            context.fill(barX, barY, barX + (int) (barW * cd), barY + 6, cd >= 1.0f ? GREEN : ACCENT);
            context.drawText(tr, Math.round(cd * 100) + "%", barX + barW + 6, barY - 1, DIM, false);

            if (WindSlamConfig.get().enabled && module != null) {
                boolean ready = module.isReadyToAttack();
                String state = ready ? "READY" : module.getBlockerReason() == null ? "WAITING" : module.getBlockerReason();
                context.drawText(tr, trim(tr, state, PANEL_W - barW - 50), barX + barW + 44, barY - 1,
                        ready ? GREEN : RED, false);
            }
        }

        if (currentTab == 3 && mobList != null) {
            context.drawText(tr, "Mob whitelist (empty = all mobs)", panelX + 12, mobList.getY() - 11, DIM, false);
        }
        if (currentTab == 4 && whitelistList != null && blacklistList != null) {
            context.drawText(tr, "Whitelist", panelX + 12, whitelistList.getY() - 11, DIM, false);
            context.drawText(tr, "Blacklist", panelX + 12, blacklistList.getY() - 11, DIM, false);
        }
    }

    private void drawSidePanel(DrawContext context, int mouseX, int mouseY) {
        TextRenderer tr = this.textRenderer;
        MinecraftClient client = MinecraftClient.getInstance();
        onlinePlayers.clear();
        if (client.world != null) {
            for (PlayerEntity p : client.world.getPlayers()) {
                if (client.player != null && p == client.player) continue;
                onlinePlayers.add(p);
            }
        }
        onlinePlayers.sort((a, b) -> a.getName().getString().compareToIgnoreCase(b.getName().getString()));

        int rowsY = panelY + 22;
        int maxRows = maxVisibleRows();
        for (int i = 0; i < onlinePlayers.size() && i < maxRows; i++) {
            PlayerEntity p = onlinePlayers.get(i);
            int rowY = rowsY + i * ONLINE_ROW_H;

            boolean hovered = mouseX >= sideX && mouseX <= sideX + sideW
                    && mouseY >= rowY && mouseY < rowY + ONLINE_ROW_H;
            if (hovered) {
                context.fill(sideX + 1, rowY, sideX + sideW - 1, rowY + ONLINE_ROW_H - 1, 0x22FFFFFF);
            }

            String name = p.getName().getString();
            WindSlamConfig config = WindSlamConfig.get();
            String prefix = "";
            int color = DIM;
            if (WindSlamConfig.containsName(config.targetWhitelist, name)) {
                prefix = "[W] ";
                color = GREEN;
            } else if (WindSlamConfig.containsName(config.blacklist, name)) {
                prefix = "[B] ";
                color = RED;
            }

            String line = prefix + name;
            if (!p.isInvisible()) {
                line += String.format(" (%.0f)", p.getHealth());
            }
            context.drawText(tr, trim(tr, line, sideW - 12), sideX + 6, rowY + 1, color, false);
        }

        // ---- nearby mobs quick-add (Mobs tab only) ----
        nearbyMobIds.clear();
        nearbyMobsY = -1;
        if (currentTab == 3 && client.world != null && client.player != null) {
            WindSlamConfig cfg = WindSlamConfig.get();
            Set<String> seen = new LinkedHashSet<>();
            for (Entity e : client.world.getEntities()) {
                if (!(e instanceof LivingEntity)) continue;
                if (e instanceof AbstractClientPlayerEntity) continue;
                if (e.squaredDistanceTo(client.player) > 48.0 * 48.0) continue;
                String id = Registries.ENTITY_TYPE.getId(e.getType()).getPath();
                if (WindSlamConfig.containsName(cfg.mobWhitelist, id)) continue;
                if (seen.add(id) && nearbyMobIds.size() < 8) {
                    nearbyMobIds.add(id);
                }
            }
            if (!nearbyMobIds.isEmpty()) {
                int startY = rowsY + Math.min(onlinePlayers.size(), maxVisibleRows()) * ONLINE_ROW_H + 16;
                if (startY + 14 + nearbyMobIds.size() * ONLINE_ROW_H <= panelY + panelH - 4) {
                    context.drawText(tr, "Nearby mobs", sideX + 6, startY, TEXT, false);
                    nearbyMobsY = startY + 12;
                    for (int i = 0; i < nearbyMobIds.size(); i++) {
                        int rowY = nearbyMobsY + i * ONLINE_ROW_H;
                        boolean hovered = mouseX >= sideX && mouseX <= sideX + sideW
                                && mouseY >= rowY && mouseY < rowY + ONLINE_ROW_H;
                        if (hovered) {
                            context.fill(sideX + 1, rowY, sideX + sideW - 1, rowY + ONLINE_ROW_H - 1, 0x22FFFFFF);
                        }
                        context.drawText(tr, "[+] " + nearbyMobIds.get(i), sideX + 6, rowY + 1,
                                hovered ? ACCENT : DIM, false);
                    }
                }
            }
        }
    }

    private int maxVisibleRows() {
        return Math.max(1, (panelH - 30) / ONLINE_ROW_H);
    }

    // ------------------------------------------------------------------ input

    // 1.21.11: mouse events arrive as Click records
    @Override
    public boolean mouseClicked(Click click, boolean doubled) {
        double mouseX = click.x();
        double mouseY = click.y();
        int button = click.button();

        if (sideVisible) {
            int rowsY = panelY + 22;
            if (mouseX >= sideX && mouseX <= sideX + sideW && mouseY >= rowsY) {
                int index = (int) ((mouseY - rowsY) / ONLINE_ROW_H);
                if (index >= 0 && index < Math.min(onlinePlayers.size(), maxVisibleRows())) {
                    String name = onlinePlayers.get(index).getName().getString();
                    WindSlamConfig config = WindSlamConfig.get();
                    List<String> list = button == 1 ? config.blacklist : config.targetWhitelist;
                    if (!WindSlamConfig.removeName(list, name)) {
                        WindSlamConfig.addName(list, name);
                    }
                    WindSlamConfig.save();
                    return true;
                }
            }
            // nearby mobs quick-add rows (Mobs tab)
            if (nearbyMobsY >= 0) {
                int idx = (int) ((mouseY - nearbyMobsY) / ONLINE_ROW_H);
                if (idx >= 0 && idx < nearbyMobIds.size()) {
                    WindSlamConfig.addName(WindSlamConfig.get().mobWhitelist, nearbyMobIds.get(idx));
                    WindSlamConfig.save();
                    return true;
                }
            }
        }

        if (whitelistList != null && whitelistList.mouseClicked(mouseX, mouseY, button)) return true;
        if (blacklistList != null && blacklistList.mouseClicked(mouseX, mouseY, button)) return true;
        if (mobList != null && mobList.mouseClicked(mouseX, mouseY, button)) return true;

        return super.mouseClicked(click, doubled);
    }

    @Override
    public boolean mouseScrolled(double mouseX, double mouseY, double horizontalAmount, double verticalAmount) {
        if (whitelistList != null && whitelistList.mouseScrolled(mouseX, mouseY, verticalAmount)) return true;
        if (blacklistList != null && blacklistList.mouseScrolled(mouseX, mouseY, verticalAmount)) return true;
        if (mobList != null && mobList.mouseScrolled(mouseX, mouseY, verticalAmount)) return true;
        return super.mouseScrolled(mouseX, mouseY, horizontalAmount, verticalAmount);
    }

    private static String trim(TextRenderer tr, String s, int maxWidth) {
        if (tr.getWidth(s) <= maxWidth) return s;
        String out = s;
        while (out.length() > 1 && tr.getWidth(out + "...") > maxWidth) {
            out = out.substring(0, out.length() - 1);
        }
        return out + "...";
    }
}
