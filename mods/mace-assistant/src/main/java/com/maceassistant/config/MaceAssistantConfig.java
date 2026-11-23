package com.maceassistant.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.maceassistant.MaceAssistantMod;
import net.fabricmc.loader.api.FabricLoader;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Global config singleton backed by a plain JSON file (Gson) in the `.minecraft/config` folder.
 * Loaded once on startup; every GUI interaction calls {@link #save()} so nothing is ever lost.
 */
public class MaceAssistantConfig {
    public enum SortMode {
        CLOSEST, LOWEST_HEALTH, HIGHEST_HEALTH, FOV;

        public SortMode next() {
            return values()[(ordinal() + 1) % values().length];
        }
    }

    public enum HudCorner {
        TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT;

        public HudCorner next() {
            return values()[(ordinal() + 1) % values().length];
        }
    }

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final Path FILE = FabricLoader.getInstance().getConfigDir().resolve("mace_assistant.json");

    private static MaceAssistantConfig INSTANCE;

    public boolean enabled = false;
    public boolean onlyWhenHolding = true;          // only activate when holding a mace
    public boolean stunSlam = true;                 // break blocking shields with axe/spear first
    public float targetRange = 6.0f;                // scan radius for finding targets
    public float reachTolerance = 0.1f;             // extra reach edge-tolerance for client/server desync
                                                    // (server always has the final say on whether a hit lands)
    public SortMode sortMode = SortMode.CLOSEST;
    public float minFallDistance = 1.5f;            // minimum fall distance before attacking
    public boolean requireFullCooldown = true;
    public int attackDelay = 2;                     // ticks between attacks
    public boolean requireLineOfSight = true;
    public boolean targetInvisible = false;
    public boolean requireCrosshair = true;         // attack only when the crosshair is on the hitbox
                                                    // (vanilla behaviour - anti-cheat sees normal swings)
    public List<String> targetWhitelist = new ArrayList<>();
    public List<String> blacklist = new ArrayList<>();
    public boolean useWhitelist = false;
    public boolean targetMobs = false;              // also target mobs (for practice dummies etc.)
    public List<String> mobWhitelist = new ArrayList<>(); // entity ids, e.g. "zombie"; empty = all mobs
    public HudCorner hudCorner = HudCorner.TOP_LEFT;
    public boolean showHud = true;                  // H key / General tab toggle

    public static MaceAssistantConfig get() {
        if (INSTANCE == null) {
            load();
        }
        return INSTANCE;
    }

    public static void load() {
        if (Files.exists(FILE)) {
            try (Reader reader = Files.newBufferedReader(FILE)) {
                INSTANCE = GSON.fromJson(reader, MaceAssistantConfig.class);
            } catch (IOException | RuntimeException e) {
                MaceAssistantMod.LOGGER.warn("[MaceAssistant] Failed to read config, using defaults", e);
            }
        }
        if (INSTANCE == null) {
            INSTANCE = new MaceAssistantConfig();
        }
    }

    /** Writes the whole config to disk. Called after every change, cheap for a file this small. */
    public static void save() {
        try {
            Files.createDirectories(FILE.getParent());
            try (Writer writer = Files.newBufferedWriter(FILE)) {
                GSON.toJson(INSTANCE, writer);
            }
        } catch (IOException e) {
            MaceAssistantMod.LOGGER.warn("[MaceAssistant] Failed to save config", e);
        }
    }

    // ---- case-insensitive helpers for the name lists ----

    public static boolean containsName(List<String> list, String name) {
        if (name == null) return false;
        for (String entry : list) {
            if (entry.equalsIgnoreCase(name)) return true;
        }
        return false;
    }

    public static boolean removeName(List<String> list, String name) {
        return list.removeIf(entry -> entry.equalsIgnoreCase(name));
    }

    public static boolean addName(List<String> list, String name) {
        if (name == null) return false;
        String trimmed = name.trim();
        if (trimmed.isEmpty() || containsName(list, trimmed)) return false;
        list.add(trimmed);
        return true;
    }
}
