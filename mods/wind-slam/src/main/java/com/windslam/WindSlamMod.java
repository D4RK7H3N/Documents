package com.windslam;

import com.windslam.config.WindSlamConfig;
import com.windslam.gui.WindSlamScreen;
import com.windslam.hud.WindSlamHud;
import com.windslam.modules.WindSlamModule;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.option.KeyBinding;
import net.minecraft.client.util.InputUtil;
import net.minecraft.util.Identifier;
import org.lwjgl.glfw.GLFW;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class WindSlamMod implements ClientModInitializer {
    public static final String MOD_ID = "windslam";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    public static KeyBinding toggleKey;
    public static KeyBinding openGuiKey;

    private static WindSlamModule module;

    @Override
    public void onInitializeClient() {
        WindSlamConfig.load();

        // 1.21.9+: keybinding categories are objects, created once from an Identifier.
        // NOTE: if mace-assistant is installed too, these default keys (V / RIGHT SHIFT)
        // will clash - rebind one mod in Options -> Controls -> WindSlam.
        KeyBinding.Category category = KeyBinding.Category.create(Identifier.of(MOD_ID, "main"));
        toggleKey = KeyBindingHelper.registerKeyBinding(new KeyBinding(
                "key.windslam.toggle", InputUtil.Type.KEYSYM, GLFW.GLFW_KEY_V, category));
        openGuiKey = KeyBindingHelper.registerKeyBinding(new KeyBinding(
                "key.windslam.gui", InputUtil.Type.KEYSYM, GLFW.GLFW_KEY_RIGHT_SHIFT, category));

        module = new WindSlamModule();
        ClientTickEvents.END_CLIENT_TICK.register(module::onTick);

        WindSlamHud.register();

        LOGGER.info("[WindSlam] Initialized.");
    }

    public static WindSlamModule getModule() {
        return module;
    }

    public static void openScreen() {
        MinecraftClient.getInstance().setScreen(new WindSlamScreen());
    }
}
