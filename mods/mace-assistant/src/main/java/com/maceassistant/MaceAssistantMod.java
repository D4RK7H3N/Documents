package com.maceassistant;

import com.maceassistant.config.MaceAssistantConfig;
import com.maceassistant.hud.MaceHud;
import com.maceassistant.modules.MaceAssistantModule;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.minecraft.client.option.KeyBinding;
import net.minecraft.client.util.InputUtil;
import net.minecraft.util.Identifier;
import org.lwjgl.glfw.GLFW;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class MaceAssistantMod implements ClientModInitializer {
    public static final String MOD_ID = "maceassistant";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    public static KeyBinding toggleKey;
    public static KeyBinding openGuiKey;
    public static KeyBinding toggleHudKey;

    private static MaceAssistantModule module;

    @Override
    public void onInitializeClient() {
        // Load config before anything reads it (GUI, HUD, module all pull from the same instance)
        MaceAssistantConfig.load();

        // 1.21.9+: keybinding categories are objects, created once from an Identifier
        KeyBinding.Category category = KeyBinding.Category.create(Identifier.of(MOD_ID, "main"));
        toggleKey = KeyBindingHelper.registerKeyBinding(new KeyBinding(
                "key.maceassistant.toggle", InputUtil.Type.KEYSYM, GLFW.GLFW_KEY_V, category));
        openGuiKey = KeyBindingHelper.registerKeyBinding(new KeyBinding(
                "key.maceassistant.gui", InputUtil.Type.KEYSYM, GLFW.GLFW_KEY_RIGHT_SHIFT, category));
        toggleHudKey = KeyBindingHelper.registerKeyBinding(new KeyBinding(
                "key.maceassistant.hud", InputUtil.Type.KEYSYM, GLFW.GLFW_KEY_H, category));

        module = new MaceAssistantModule();
        ClientTickEvents.END_CLIENT_TICK.register(module::onTick);

        MaceHud.register();

        LOGGER.info("[MaceAssistant] Initialized.");
    }

    public static MaceAssistantModule getModule() {
        return module;
    }
}
