package com.windslam.gui;

import net.minecraft.client.font.TextRenderer;
import net.minecraft.client.gui.DrawContext;

import java.util.List;

/**
 * Minimal scrollable name list with a right-edge remove ("x") zone per entry.
 * Backs directly onto a live config list; {@code onChange} persists after mutations.
 */
public class TargetListWidget {

    private static final int ENTRY_H = 12;
    private static final int REMOVE_ZONE = 16;

    private final TextRenderer textRenderer;
    private final List<String> entries;
    private final Runnable onChange;

    private final int x;
    private final int y;
    private final int width;
    private final int height;
    private int scrollOffset = 0;

    public TargetListWidget(TextRenderer textRenderer, int x, int y, int width, int height,
                            List<String> entries, Runnable onChange) {
        this.textRenderer = textRenderer;
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.entries = entries;
        this.onChange = onChange;
    }

    public void render(DrawContext context, int mouseX, int mouseY) {
        context.fill(x - 1, y - 1, x + width + 1, y + height + 1, 0xFF26303F);
        context.fill(x, y, x + width, y + height, 0x800C1119);

        int visible = height / ENTRY_H;
        int end = Math.min(scrollOffset + visible, entries.size());

        for (int i = scrollOffset; i < end; i++) {
            int entryY = y + (i - scrollOffset) * ENTRY_H;
            boolean hovered = isInside(mouseX, mouseY) && mouseY >= entryY && mouseY < entryY + ENTRY_H;
            if (hovered) {
                context.fill(x, entryY, x + width, entryY + ENTRY_H, 0x22FFFFFF);
            }
            context.drawText(textRenderer, trim(entries.get(i), width - REMOVE_ZONE - 6),
                    x + 4, entryY + 2, 0xFFDDE3EE, false);

            boolean removeHover = hovered && mouseX >= x + width - REMOVE_ZONE;
            context.drawText(textRenderer, "x", x + width - 9, entryY + 2,
                    removeHover ? 0xFFE74C3C : 0xFF6B7688, false);
        }

        if (entries.size() * ENTRY_H > height) {
            float frac = (float) height / (entries.size() * ENTRY_H);
            int thumbH = Math.max(10, (int) (height * frac));
            int maxScroll = entries.size() - visible;
            int thumbY = y + (maxScroll == 0 ? 0 : (int) ((height - thumbH) * ((float) scrollOffset / maxScroll)));
            context.fill(x + width - 2, thumbY, x + width, thumbY + thumbH, 0xFF4A5568);
        }
    }

    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if (!isInside(mouseX, mouseY)) return false;
        if (!entries.isEmpty()) {
            int index = scrollOffset + (int) ((mouseY - y) / ENTRY_H);
            if (index >= 0 && index < entries.size() && mouseX >= x + width - REMOVE_ZONE) {
                entries.remove(index);
                int maxScroll = Math.max(0, entries.size() - height / ENTRY_H);
                scrollOffset = Math.min(scrollOffset, maxScroll);
                onChange.run();
            }
        }
        return true;
    }

    public boolean mouseScrolled(double mouseX, double mouseY, double verticalAmount) {
        if (!isInside(mouseX, mouseY)) return false;
        int maxScroll = Math.max(0, entries.size() - height / ENTRY_H);
        scrollOffset = Math.max(0, Math.min(maxScroll,
                scrollOffset - (int) Math.signum(verticalAmount)));
        return true;
    }

    public boolean isInside(double px, double py) {
        return px >= x && px <= x + width && py >= y && py <= y + height;
    }

    public int getY() {
        return y;
    }

    private String trim(String s, int maxWidth) {
        if (textRenderer.getWidth(s) <= maxWidth) return s;
        String out = s;
        while (out.length() > 1 && textRenderer.getWidth(out + "...") > maxWidth) {
            out = out.substring(0, out.length() - 1);
        }
        return out + "...";
    }
}
