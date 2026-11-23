package com.windslam.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.windslam.WindSlamMod;
import net.fabricmc.loader.api.FabricLoader;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Global config singleton backed by JSON in the config folder.
 * Loaded on startup; every GUI change calls {@link #save()}.
 */
public class WindSlamConfig {
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
    private static final Path FILE = FabricLoader.getInstance().getConfigDir().resolve("wind_slam.json");

    private static WindSlamConfig INSTANCE;

    // core
    public boolean enabled = false;
    public boolean onlyWhenHolding = true;          // mace slam requires holding the mace
    public boolean stunSlam = true;                 // axe shield-break while target blocks

    // wind launch
    public boolean autoWindLaunch = true;           // auto throw wind charge to launch
    public boolean jumpOnThrow = true;              // jump timed with the throw for extra height
    public float launchTriggerRange = 5.0f;         // throw when target is this close
    public int windChargeCooldown = 20;             // custom min ticks between launches (server = 1s)

    // auto sprint
    public boolean autoSprint = true;               // force sprint while engaged (incl. mid-air)

    // general combat
    public float targetRange = 6.0f;                // scan radius for targets
    public float reachTolerance = 0.1f;             // edge tolerance for hit attempts
    public SortMode sortMode = SortMode.CLOSEST;
    public float minFallDistance = 1.5f;            // slam only fires past this fall distance
    public boolean requireFullCooldown = true;
    public int attackDelay = 2;                     // min ticks between attacks
    public boolean requireLineOfSight = true;
    public boolean targetInvisible = false;
    public boolean requireCrosshair = true;         // swing only when the crosshair is on the hitbox

    // lists
    public List<String> targetWhitelist = new ArrayList<>();
    public List<String> blacklist = new ArrayList<>();
    public boolean useWhitelist = false;
    public boolean targetMobs = false;
    public List<String> mobWhitelist = new ArrayList<>(); // empty = all mobs

    public HudCorner hudCorner = HudCorner.TOP_LEFT;

    public static WindSlamConfig get() {
        if (INSTANCE == null) {
            load();
        }
        return INSTANCE;
    }

    public static void load() {
        if (Files.exists(FILE)) {
            try (Reader reader = Files.newBufferedReader(FILE)) {
                INSTANCE = GSON.fromJson(reader, WindSlamConfig.class);
            } catch (IOException | RuntimeException e) {
                WindSlamMod.LOGGER.warn("[WindSlam] Failed to read config, using defaults", e);
            }
        }
        if (INSTANCE == null) {
            INSTANCE = new WindSlamConfig();
        }
    }

    public static void save() {
        try {
            Files.createDirectories(FILE.getParent());
            try (Writer writer = Files.newBufferedWriter(FILE)) {
                GSON.toJson(INSTANCE, writer);
            }
        } catch (IOException e) {
            WindSlamMod.LOGGER.warn("[WindSlam] Failed to save config", e);
        }
    }

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
