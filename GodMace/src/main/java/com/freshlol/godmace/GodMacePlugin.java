package com.freshlol.godmace;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.GameMode;
import org.bukkit.NamespacedKey;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import com.destroystokyo.paper.event.player.PlayerArmorChangeEvent;
import org.bukkit.attribute.Attribute;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.boss.BarColor;
import org.bukkit.boss.BarStyle;
import org.bukkit.boss.BossBar;
import org.bukkit.entity.Arrow;
import org.bukkit.entity.Entity;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.Display;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.entity.Skeleton;
import org.bukkit.entity.Villager;
import org.bukkit.entity.Warden;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.entity.VillagerAcquireTradeEvent;
import org.bukkit.event.inventory.CraftItemEvent;
import org.bukkit.event.inventory.PrepareItemCraftEvent;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.MerchantRecipe;
import org.bukkit.inventory.PlayerInventory;
import org.bukkit.inventory.ShapedRecipe;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.util.Transformation;
import org.bukkit.scheduler.BukkitTask;
import org.bukkit.util.Vector;
import org.joml.Quaternionf;
import org.joml.Vector3f;

import java.util.*;

public class GodMacePlugin extends JavaPlugin implements Listener, CommandExecutor {

    private NamespacedKey maceLevelKey;
    private NamespacedKey godArmorKey;
    private NamespacedKey crownRecipeKey;
    private final Map<UUID, Long> dashCooldownEnd = new HashMap<>();
    private final Set<UUID> fallImmunity = new HashSet<>();

    // --- Combo tracking ---
    private final Map<UUID, Integer> comboCount = new HashMap<>();
    private final Map<UUID, Long> lastHitTime = new HashMap<>();
    private static final long COMBO_WINDOW_MS = 3000;
    private static final int MAX_COMBO = 10;
    private static final double COMBO_DAMAGE_PER_STACK = 1.5;

    // --- Ban ability & Second Wind ---
    private static final String BAN_PERMISSION = "godmace.banability";
    private static final long SECOND_WIND_COOLDOWN_MS = 180000; // 3 minutes
    private final Map<UUID, Long> secondWindCooldown = new HashMap<>();

    // Guards against the Godly-tier AoE shockwave re-triggering itself recursively
    // (target.damage() fires a new EntityDamageByEntityEvent from the same attacker)
    private final Set<UUID> smiteInProgress = new HashSet<>();

    // --- Legendary weapons (God Spear / God Sword) & bosses ---
    private NamespacedKey legendaryWeaponKey;
    private NamespacedKey bossTagKey;
    private NamespacedKey treasureMapTypeKey;
    private NamespacedKey treasureMapXKey;
    private NamespacedKey treasureMapZKey;
    private final Map<UUID, Long> spearCooldownEnd = new HashMap<>();
    private final Map<UUID, Long> swordCooldownEnd = new HashMap<>();
    private static final long SPEAR_COOLDOWN_MS = 6000;
    private static final long SWORD_COOLDOWN_MS = 12000;
    private static final double MAP_TRIGGER_RADIUS = 15.0;
    private static final double BOSS_BAR_RADIUS = 80.0;
    private final Map<UUID, BossBar> activeBossBars = new HashMap<>();
    private final Set<UUID> bossPhaseTwoTriggered = new HashSet<>();

    // --- Boss attack AI (scheduler-driven ability loops) ---
    private final Map<UUID, BukkitTask> bossAttackTasks = new HashMap<>();
    private final Map<UUID, Map<String, Long>> abilityCooldowns = new HashMap<>();
    private final Map<UUID, Set<UUID>> bossGuards = new HashMap<>();
    private static final double BOSS_ABILITY_RANGE = 24.0;
    private static final long GUARD_LIFETIME_TICKS = 600L; // 30s
    private static final int MAX_GUARDS_ALIVE = 6;

    // --- Custom Display Entity models (set these to match your Blockbench export's Custom Model Data) ---
    private static final int WARDEN_MODEL_DATA = 100001;
    private static final int SKELETON_MODEL_DATA = 100002;
    private final Map<UUID, ItemDisplay> bossDisplayModels = new HashMap<>();

    private final Random rng = new Random();

    @Override
    public void onEnable() {
        this.maceLevelKey = new NamespacedKey(this, "mace_kills");
        this.godArmorKey = new NamespacedKey(this, "god_armor");
        this.crownRecipeKey = new NamespacedKey(this, "crown_of_the_gods");
        this.legendaryWeaponKey = new NamespacedKey(this, "legendary_weapon");
        this.bossTagKey = new NamespacedKey(this, "boss_tag");
        this.treasureMapTypeKey = new NamespacedKey(this, "treasure_map_type");
        this.treasureMapXKey = new NamespacedKey(this, "treasure_map_x");
        this.treasureMapZKey = new NamespacedKey(this, "treasure_map_z");
        getServer().getPluginManager().registerEvents(this, this);
        Objects.requireNonNull(getCommand("getgodmace")).setExecutor(this);
        registerCrownRecipe();

        // Loop every second: mace/armor passive buffs, and treasure map holders' proximity check
        Bukkit.getScheduler().runTaskTimer(this, () -> {
            for (Player p : Bukkit.getOnlinePlayers()) {
                ItemStack item = p.getInventory().getItemInMainHand();
                if (getMaceKills(item) >= 15) {
                    p.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 39, 1, false, false, true));
                    p.addPotionEffect(new PotionEffect(PotionEffectType.STRENGTH, 39, 1, false, false, true));
                    p.addPotionEffect(new PotionEffect(PotionEffectType.RESISTANCE, 39, 0, false, false, true));
                }

                if (isWearingFullGodArmor(p)) {
                    p.addPotionEffect(new PotionEffect(PotionEffectType.REGENERATION, 39, 1, false, false, true));
                    p.addPotionEffect(new PotionEffect(PotionEffectType.FIRE_RESISTANCE, 39, 0, false, false, true));
                    p.addPotionEffect(new PotionEffect(PotionEffectType.RESISTANCE, 39, 0, false, false, true));
                    p.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 39, 0, false, false, true));
                }

                checkTreasureMapProximity(p, item);
            }

            updateBossBars();
        }, 20L, 20L);

        // Faster loop just for keeping custom boss models facing the right way
        Bukkit.getScheduler().runTaskTimer(this, () -> {
            for (Map.Entry<UUID, ItemDisplay> entry : bossDisplayModels.entrySet()) {
                Entity boss = Bukkit.getEntity(entry.getKey());
                ItemDisplay display = entry.getValue();
                if (boss == null || display == null || !display.isValid()) continue;
                Location displayLoc = display.getLocation();
                displayLoc.setYaw(boss.getLocation().getYaw());
                display.teleport(displayLoc);
            }
        }, 0L, 2L);
    }

    // Spawns a Display Entity "puppet" riding the (invisible) boss, showing a custom model
    // via Custom Model Data. Design the actual model/texture in Blockbench and export it into
    // a resource pack referencing the same customModelData value used here.
    private ItemDisplay attachBossModel(LivingEntity boss, int customModelData, float scale) {
        boss.setInvisible(true);

        ItemStack modelItem = new ItemStack(Material.PAPER);
        ItemMeta meta = modelItem.getItemMeta();
        meta.setCustomModelData(customModelData);
        modelItem.setItemMeta(meta);

        ItemDisplay display = boss.getWorld().spawn(boss.getLocation(), ItemDisplay.class);
        display.setItemStack(modelItem);
        display.setBillboard(Display.Billboard.FIXED);
        display.setInterpolationDuration(3);
        display.setInterpolationDelay(0);
        display.setTransformation(new Transformation(
                new Vector3f(0f, 0f, 0f),
                new Quaternionf(),
                new Vector3f(scale, scale, scale),
                new Quaternionf()
        ));

        boss.addPassenger(display);
        bossDisplayModels.put(boss.getUniqueId(), display);
        return display;
    }

    // --- CROWN CRAFTING RECIPE ---
    // [Netherite] [ empty ] [Netherite]
    // [GhastTear] [NetherStar] [GhastTear]
    // [ Gold ]    [DriedGhast] [ Gold ]
    private void registerCrownRecipe() {
        ItemStack crown = createGodArmorPiece(Material.NETHERITE_HELMET, "§6§l✧ CROWN OF THE GODS ✧", "Helmet");
        ShapedRecipe recipe = new ShapedRecipe(crownRecipeKey, crown);
        recipe.shape("N N", "TST", "GDG");
        recipe.setIngredient('N', Material.NETHERITE_INGOT);
        recipe.setIngredient('T', Material.GHAST_TEAR);
        recipe.setIngredient('S', Material.NETHER_STAR);
        recipe.setIngredient('G', Material.GOLD_INGOT);
        recipe.setIngredient('D', Material.DRIED_GHAST);
        getServer().addRecipe(recipe);
    }

    // Only admins may craft the Crown at all — non-admins never see a result item
    @EventHandler
    public void onPrepareCraftCrown(PrepareItemCraftEvent event) {
        if (!(event.getRecipe() instanceof org.bukkit.Keyed keyed)) return;
        if (!keyed.getKey().equals(crownRecipeKey)) return;
        if (!(event.getView().getPlayer() instanceof Player player)) return;

        if (!player.hasPermission("godmace.admin")) {
            event.getInventory().setResult(null);
        }
    }

    // Crafting the Crown also grants the rest of the God Armor set
    @EventHandler
    public void onCraftCrown(CraftItemEvent event) {
        if (!(event.getRecipe() instanceof org.bukkit.Keyed keyed)) return;
        if (!keyed.getKey().equals(crownRecipeKey)) return;
        if (!(event.getWhoClicked() instanceof Player player)) return;

        // Wait a tick so the crafting transaction (giving the Crown) finishes first
        Bukkit.getScheduler().runTask(this, () -> {
            PlayerInventory inv = player.getInventory();
            inv.addItem(
                    createGodArmorPiece(Material.NETHERITE_CHESTPLATE, "§6§l✧ CHESTPLATE OF THE GODS ✧", "Chestplate"),
                    createGodArmorPiece(Material.NETHERITE_LEGGINGS, "§6§l✧ LEGGINGS OF THE GODS ✧", "Leggings"),
                    createGodArmorPiece(Material.NETHERITE_BOOTS, "§6§l✧ BOOTS OF THE GODS ✧", "Boots")
            );
            player.playSound(player.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1f, 0.7f);
            player.getWorld().spawnParticle(Particle.TOTEM_OF_UNDYING, player.getLocation().add(0, 1, 0), 40, 0.5, 1, 0.5, 0.3);
            player.sendMessage("§6§l✧ §fThe Crown has bestowed the rest of the §6§lGOD ARMOR §fset upon you!");
        });
    }

    private ItemStack createGodArmorPiece(Material material, String name, String slotLabel) {
        ItemStack item = new ItemStack(material);
        ItemMeta meta = item.getItemMeta();
        if (meta == null) return item;

        meta.setDisplayName(name);
        meta.getPersistentDataContainer().set(godArmorKey, PersistentDataType.BYTE, (byte) 1);
        meta.setUnbreakable(true);
        meta.addEnchant(Enchantment.PROTECTION, 10, true);
        meta.addEnchant(Enchantment.MENDING, 1, true);
        meta.addEnchant(Enchantment.THORNS, 3, true);
        meta.addEnchant(Enchantment.BINDING_CURSE, 1, true);
        meta.addItemFlags(ItemFlag.HIDE_ENCHANTS, ItemFlag.HIDE_UNBREAKABLE);

        List<String> lore = new ArrayList<>();
        lore.add("§7Piece: §e" + slotLabel);
        lore.add("");
        lore.add("§5§l★ SET: GOD ARMOR");
        lore.add("§c§lCurse of Binding §7(cannot be removed while worn)");
        lore.add("§b§lUnbreakable");
        lore.add("§6• Full Set Bonus: §fRegen II, Fire Resist,");
        lore.add("  §fResistance I, Speed I, No Fall Damage");
        lore.add("§6• Second Wind: §fEmergency heal below 20% HP §7(3min cd)");
        meta.setLore(lore);

        item.setItemMeta(meta);
        return item;
    }

    private boolean isWearingFullGodArmor(Player player) {
        PlayerInventory inv = player.getInventory();
        return isGodArmorPiece(inv.getHelmet())
                && isGodArmorPiece(inv.getChestplate())
                && isGodArmorPiece(inv.getLeggings())
                && isGodArmorPiece(inv.getBoots());
    }

    // ================= TREASURE MAPS & BOSSES (God Spear / God Sword) =================

    // Cartographer villagers occasionally offer a treasure map trade
    @EventHandler
    public void onVillagerAcquireTrade(VillagerAcquireTradeEvent event) {
        if (!(event.getEntity() instanceof Villager villager)) return;
        if (villager.getProfession() != Villager.Profession.CARTOGRAPHER) return;
        if (rng.nextDouble() > 0.12) return; // ~12% chance per trade slot generated

        boolean warden = rng.nextBoolean();
        ItemStack mapItem = createTreasureMap(warden ? "warden" : "skeleton", villager.getLocation());

        MerchantRecipe recipe = new MerchantRecipe(mapItem, 0, 1, false);
        recipe.addIngredient(new ItemStack(Material.EMERALD, 30));
        recipe.addIngredient(new ItemStack(Material.PAPER, 8));
        event.setRecipe(recipe);
    }

    private ItemStack createTreasureMap(String bossType, Location reference) {
        Location target = findRandomTreasureLocation(reference);
        boolean warden = bossType.equals("warden");

        ItemStack map = new ItemStack(Material.COMPASS);
        ItemMeta meta = map.getItemMeta();
        meta.setDisplayName(warden ? "§4§lWarden Treasure Map" : "§8§lSkeleton Treasure Map");

        List<String> lore = new ArrayList<>();
        lore.add("§7A mysterious compass humming with power.");
        lore.add(warden ? "§7Leads to §4the Elder Warden's§7 lair." : "§7Leads to §8the Crowned Skeleton's§7 lair.");
        lore.add("");
        lore.add("§8Target: X=" + target.getBlockX() + " Z=" + target.getBlockZ());
        lore.add("§7Hold this and follow the needle.");
        meta.setLore(lore);

        meta.getPersistentDataContainer().set(treasureMapTypeKey, PersistentDataType.STRING, bossType);
        meta.getPersistentDataContainer().set(treasureMapXKey, PersistentDataType.INTEGER, target.getBlockX());
        meta.getPersistentDataContainer().set(treasureMapZKey, PersistentDataType.INTEGER, target.getBlockZ());
        map.setItemMeta(meta);
        return map;
    }

    // Picks a random far-off point (approximating "unexplored"), avoiding water/void landings
    private Location findRandomTreasureLocation(Location reference) {
        World world = reference.getWorld();
        for (int attempt = 0; attempt < 8; attempt++) {
            double angle = rng.nextDouble() * Math.PI * 2;
            double distance = 500 + rng.nextDouble() * 2500; // 500-3000 blocks out
            int x = (int) (reference.getX() + Math.cos(angle) * distance);
            int z = (int) (reference.getZ() + Math.sin(angle) * distance);
            int y = world.getHighestBlockYAt(x, z);
            Material ground = world.getBlockAt(x, y - 1, z).getType();
            if (ground != Material.WATER && ground != Material.LAVA && y > world.getMinHeight() + 5) {
                return new Location(world, x + 0.5, y, z + 0.5);
            }
        }
        // Fallback: accept whatever the last roll gives, even if imperfect
        double angle = rng.nextDouble() * Math.PI * 2;
        int x = (int) (reference.getX() + Math.cos(angle) * 1000);
        int z = (int) (reference.getZ() + Math.sin(angle) * 1000);
        int y = world.getHighestBlockYAt(x, z);
        return new Location(world, x + 0.5, y, z + 0.5);
    }

    // Every tick-loop pass: keep the compass pointed at the target, and trigger the boss on arrival
    private void checkTreasureMapProximity(Player p, ItemStack heldItem) {
        if (heldItem == null || !heldItem.hasItemMeta()) return;
        var pdc = heldItem.getItemMeta().getPersistentDataContainer();
        String bossType = pdc.get(treasureMapTypeKey, PersistentDataType.STRING);
        if (bossType == null) return;

        Integer targetX = pdc.get(treasureMapXKey, PersistentDataType.INTEGER);
        Integer targetZ = pdc.get(treasureMapZKey, PersistentDataType.INTEGER);
        if (targetX == null || targetZ == null) return;

        World world = p.getWorld();
        Location target = new Location(world, targetX + 0.5, world.getHighestBlockYAt(targetX, targetZ), targetZ + 0.5);
        p.setCompassTarget(target);

        double dx = p.getLocation().getX() - target.getX();
        double dz = p.getLocation().getZ() - target.getZ();
        double flatDistanceSq = dx * dx + dz * dz;
        if (flatDistanceSq > MAP_TRIGGER_RADIUS * MAP_TRIGGER_RADIUS) return;

        // Arrived — consume the map and summon the boss
        heldItem.setAmount(heldItem.getAmount() - 1);
        Location spawnLoc = target.clone().add(0, 1, 0);
        if (bossType.equals("warden")) {
            spawnWardenBoss(spawnLoc);
            Bukkit.broadcastMessage("§4§l⚠ " + p.getName() + " has awoken §4§lTHE ELDER WARDEN§r§4§l! ⚠");
        } else {
            spawnSkeletonBoss(spawnLoc);
            Bukkit.broadcastMessage("§8§l☠ " + p.getName() + " has awoken §8§lTHE CROWNED SKELETON§r§8§l! ☠");
        }
        p.playSound(p.getLocation(), Sound.ENTITY_WITHER_SPAWN, 1.5f, 1f);
    }

    private void spawnWardenBoss(Location loc) {
        Warden warden = loc.getWorld().spawn(loc, Warden.class);
        warden.getAttribute(Attribute.MAX_HEALTH).setBaseValue(5000);
        warden.setHealth(5000);
        warden.getAttribute(Attribute.SCALE).setBaseValue(2.5); // Massive Elder Warden
        warden.setGlowing(true);
        warden.setCustomName("§4§l⚠ THE ELDER WARDEN ⚠");
        warden.setCustomNameVisible(true);
        warden.getPersistentDataContainer().set(bossTagKey, PersistentDataType.STRING, "warden");
        attachBossModel(warden, WARDEN_MODEL_DATA, 2.5f);

        BossBar bar = Bukkit.createBossBar("§4§l⚠ THE ELDER WARDEN ⚠", BarColor.RED, BarStyle.SEGMENTED_10);
        bar.setProgress(1.0);
        activeBossBars.put(warden.getUniqueId(), bar);

        startBossAttackTask(warden.getUniqueId(), "warden");
    }

    private void spawnSkeletonBoss(Location loc) {
        Skeleton skeleton = loc.getWorld().spawn(loc, Skeleton.class);
        skeleton.getAttribute(Attribute.MAX_HEALTH).setBaseValue(3000);
        skeleton.setHealth(3000);
        skeleton.getAttribute(Attribute.SCALE).setBaseValue(2.5); // Massive Crowned Skeleton
        skeleton.setGlowing(true);
        skeleton.setCustomName("§8§l☠ THE CROWNED SKELETON ☠");
        skeleton.setCustomNameVisible(true);
        skeleton.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, Integer.MAX_VALUE, 1, false, false, false));
        skeleton.addPotionEffect(new PotionEffect(PotionEffectType.STRENGTH, Integer.MAX_VALUE, 2, false, false, false));

        // --- Dual-wielded netherite swords (cosmetic glow, never drop) ---
        var equip = skeleton.getEquipment();
        equip.setItemInMainHand(createRoyalSword());
        equip.setItemInOffHand(createRoyalSword());
        equip.setItemInMainHandDropChance(0f);
        equip.setItemInOffHandDropChance(0f);

        // --- Royal visual kit: crown, cape, boots (all purely cosmetic, never drop) ---
        ItemStack crown = new ItemStack(Material.GOLDEN_HELMET);
        ItemMeta crownMeta = crown.getItemMeta();
        crownMeta.setUnbreakable(true);
        crownMeta.addItemFlags(ItemFlag.HIDE_UNBREAKABLE);
        crown.setItemMeta(crownMeta);

        ItemStack cape = new ItemStack(Material.ELYTRA);
        ItemMeta capeMeta = cape.getItemMeta();
        capeMeta.setUnbreakable(true);
        capeMeta.addItemFlags(ItemFlag.HIDE_UNBREAKABLE);
        cape.setItemMeta(capeMeta);

        ItemStack royalBoots = new ItemStack(Material.GOLDEN_BOOTS);
        ItemMeta bootsMeta = royalBoots.getItemMeta();
        bootsMeta.setUnbreakable(true);
        bootsMeta.addItemFlags(ItemFlag.HIDE_UNBREAKABLE);
        royalBoots.setItemMeta(bootsMeta);

        equip.setHelmet(crown);
        equip.setChestplate(cape);
        equip.setBoots(royalBoots);
        equip.setHelmetDropChance(0f);
        equip.setChestplateDropChance(0f);
        equip.setBootsDropChance(0f);

        skeleton.getPersistentDataContainer().set(bossTagKey, PersistentDataType.STRING, "skeleton");
        attachBossModel(skeleton, SKELETON_MODEL_DATA, 2.5f);

        BossBar bar = Bukkit.createBossBar("§8§l☠ THE CROWNED SKELETON ☠", BarColor.WHITE, BarStyle.SEGMENTED_10);
        bar.setProgress(1.0);
        activeBossBars.put(skeleton.getUniqueId(), bar);

        startBossAttackTask(skeleton.getUniqueId(), "skeleton");
    }

    private ItemStack createRoyalSword() {
        ItemStack sword = new ItemStack(Material.NETHERITE_SWORD);
        ItemMeta meta = sword.getItemMeta();
        meta.setDisplayName("§8§l☠ Royal Blade ☠");
        meta.setUnbreakable(true);
        meta.addEnchant(Enchantment.SHARPNESS, 5, true);
        meta.addItemFlags(ItemFlag.HIDE_UNBREAKABLE);
        sword.setItemMeta(meta);
        return sword;
    }

    // ================= BOSS ATTACK AI (scheduler-driven ability loops) =================

    private void startBossAttackTask(UUID bossId, String type) {
        BukkitTask task = Bukkit.getScheduler().runTaskTimer(this, () -> {
            Entity e = Bukkit.getEntity(bossId);
            if (!(e instanceof LivingEntity boss) || boss.isDead() || !boss.isValid()) {
                cleanupBoss(bossId);
                return;
            }
            runBossAttackTick(boss, type);
        }, 20L, 20L);
        bossAttackTasks.put(bossId, task);
    }

    private void runBossAttackTick(LivingEntity boss, String type) {
        Player target = findNearestTarget(boss, BOSS_ABILITY_RANGE);
        if (target == null) return;

        double max = boss.getAttribute(Attribute.MAX_HEALTH).getValue();
        boolean phaseTwo = boss.getHealth() <= max * 0.5;
        UUID id = boss.getUniqueId();

        if (type.equals("warden")) {
            if (phaseTwo && tryAbility(id, "abyssal_pull", 8000)) { castAbyssalPull((Warden) boss); return; }
            if (tryAbility(id, "tremor_slam", phaseTwo ? 6000 : 9000)) { castTremorSlam((Warden) boss); return; }
            if (tryAbility(id, "sonic_barrage", phaseTwo ? 4000 : 6000)) { castSonicBarrage((Warden) boss, target); return; }
        } else if (type.equals("skeleton")) {
            if (phaseTwo && tryAbility(id, "kings_judgment", 8000)) { castKingsJudgment((Skeleton) boss, target); return; }
            if (tryAbility(id, "summon_court", phaseTwo ? 9000 : 14000)) { castSummonCourt((Skeleton) boss); return; }
            if (tryAbility(id, "blade_whirlwind", phaseTwo ? 6500 : 10000)) { castBladeWhirlwind((Skeleton) boss, phaseTwo); return; }
            if (tryAbility(id, "twin_cleave", phaseTwo ? 3500 : 5000)) { castTwinCleave((Skeleton) boss, target); return; }
        }
    }

    // Stamps the ability's cooldown and returns true if it was off cooldown (ready to cast)
    private boolean tryAbility(UUID bossId, String ability, long cooldownMs) {
        long now = System.currentTimeMillis();
        Map<String, Long> cds = abilityCooldowns.computeIfAbsent(bossId, k -> new HashMap<>());
        Long readyAt = cds.get(ability);
        if (readyAt != null && readyAt > now) return false;
        cds.put(ability, now + cooldownMs);
        return true;
    }

    private Player findNearestTarget(LivingEntity boss, double range) {
        Player nearest = null;
        double nearestDistSq = range * range;
        for (Player p : boss.getWorld().getPlayers()) {
            if (p.getGameMode() == GameMode.CREATIVE || p.getGameMode() == GameMode.SPECTATOR) continue;
            double dSq = p.getLocation().distanceSquared(boss.getLocation());
            if (dSq <= nearestDistSq) {
                nearestDistSq = dSq;
                nearest = p;
            }
        }
        return nearest;
    }

    // Cancels the attack task, clears cooldowns, and despawns any living guards
    private void cleanupBoss(UUID bossId) {
        BukkitTask task = bossAttackTasks.remove(bossId);
        if (task != null) task.cancel();
        abilityCooldowns.remove(bossId);
        Set<UUID> guards = bossGuards.remove(bossId);
        if (guards != null) {
            for (UUID gid : guards) {
                Entity g = Bukkit.getEntity(gid);
                if (g != null && g.isValid()) g.remove();
            }
        }
    }

    private void drawRing(Location center, double radius, Particle particle) {
        World w = center.getWorld();
        for (double a = 0; a < Math.PI * 2; a += Math.PI / 16) {
            Location p = center.clone().add(Math.cos(a) * radius, 0.2, Math.sin(a) * radius);
            w.spawnParticle(particle, p, 1, 0, 0, 0, 0);
        }
    }

    // --- ELDER WARDEN abilities ---

    // Fires 3 sonic boom beams in a spread toward the target (hitscan along each beam)
    private void castSonicBarrage(Warden warden, Player target) {
        World w = warden.getWorld();
        w.playSound(warden.getLocation(), Sound.ENTITY_WARDEN_ROAR, 2f, 0.8f);
        Location start = warden.getLocation().add(0, 2.0, 0);
        Vector baseDir = target.getEyeLocation().toVector().subtract(start.toVector()).normalize();

        for (int i = 0; i < 3; i++) {
            double spread = (i - 1) * 0.18;
            double cos = Math.cos(spread), sin = Math.sin(spread);
            Vector dir = baseDir.clone();
            double nx = dir.getX() * cos - dir.getZ() * sin;
            double nz = dir.getX() * sin + dir.getZ() * cos;
            dir.setX(nx).setZ(nz).normalize();
            fireSonicBeam(warden, start.clone(), dir);
        }
    }

    private void fireSonicBeam(Warden warden, Location start, Vector dir) {
        World w = warden.getWorld();
        Set<UUID> hit = new HashSet<>();
        for (double d = 0; d <= 20.0; d += 1.0) {
            Location point = start.clone().add(dir.clone().multiply(d));
            w.spawnParticle(Particle.SONIC_BOOM, point, 1, 0, 0, 0, 0);
            for (Entity e : w.getNearbyEntities(point, 1.0, 1.0, 1.0)) {
                if (e instanceof LivingEntity le && !e.equals(warden) && hit.add(e.getUniqueId())) {
                    le.damage(10.0, warden);
                    le.setVelocity(dir.clone().multiply(1.2).setY(0.4));
                }
            }
        }
    }

    // Telegraphs a 6-block ring, then slams for AoE damage + launch
    private void castTremorSlam(Warden warden) {
        Location center = warden.getLocation();
        World w = warden.getWorld();
        w.playSound(center, Sound.ENTITY_WARDEN_TENDRIL_CLICKS, 2f, 0.7f);
        for (int t = 0; t < 4; t++) {
            Bukkit.getScheduler().runTaskLater(this, () -> drawRing(center, 6.0, Particle.SCULK_SOUL), t * 5L);
        }
        Bukkit.getScheduler().runTaskLater(this, () -> {
            if (!warden.isValid()) return;
            w.playSound(center, Sound.ENTITY_WARDEN_ATTACK_IMPACT, 2f, 0.6f);
            w.spawnParticle(Particle.EXPLOSION_EMITTER, center, 2);
            for (Entity e : w.getNearbyEntities(center, 6, 3, 6)) {
                if (e instanceof LivingEntity le && !e.equals(warden)) {
                    le.damage(14.0, warden);
                    le.setVelocity(le.getLocation().toVector().subtract(center.toVector()).normalize().multiply(0.8).setY(0.9));
                }
            }
        }, 20L);
    }

    // Phase 2: drags all nearby players in and blinds them with Darkness
    private void castAbyssalPull(Warden warden) {
        Location center = warden.getLocation();
        World w = warden.getWorld();
        w.playSound(center, Sound.ENTITY_WARDEN_ROAR, 2f, 0.5f);
        w.spawnParticle(Particle.SCULK_SOUL, center.clone().add(0, 1.5, 0), 60, 2, 2, 2, 0.1);
        for (Player p : w.getPlayers()) {
            if (p.getLocation().distanceSquared(center) <= 12 * 12) {
                Vector pull = center.toVector().subtract(p.getLocation().toVector()).normalize().multiply(1.5);
                pull.setY(0.3);
                p.setVelocity(pull);
                p.addPotionEffect(new PotionEffect(PotionEffectType.DARKNESS, 80, 0, false, false, true));
            }
        }
    }

    // --- CROWNED SKELETON abilities ---

    // Dashes at the target and slashes twice in quick succession
    private void castTwinCleave(Skeleton king, Player target) {
        World w = king.getWorld();
        Vector dash = target.getLocation().toVector().subtract(king.getLocation().toVector()).normalize().multiply(1.8);
        dash.setY(0.2);
        king.setVelocity(dash);
        w.playSound(king.getLocation(), Sound.ENTITY_SKELETON_AMBIENT, 1.5f, 0.6f);
        for (int s = 0; s < 2; s++) {
            Bukkit.getScheduler().runTaskLater(this, () -> {
                if (!king.isValid()) return;
                w.playSound(king.getLocation(), Sound.ENTITY_PLAYER_ATTACK_SWEEP, 1.5f, 0.8f);
                w.spawnParticle(Particle.SWEEP_ATTACK, king.getLocation().add(0, 1.5, 0), 8, 1.5, 0.5, 1.5, 0.1);
                for (Entity e : king.getNearbyEntities(3.5, 2, 3.5)) {
                    if (e instanceof LivingEntity le && !e.equals(king)) {
                        le.damage(9.0, king);
                        le.setVelocity(le.getLocation().toVector().subtract(king.getLocation().toVector()).normalize().multiply(0.6).setY(0.3));
                    }
                }
            }, 6L + s * 8L);
        }
    }

    // Telegraphs a ring, then spins for AoE damage + outward fling
    private void castBladeWhirlwind(Skeleton king, boolean phaseTwo) {
        double radius = phaseTwo ? 6.0 : 5.0;
        Location center = king.getLocation();
        World w = king.getWorld();
        w.playSound(center, Sound.ENTITY_SKELETON_AMBIENT, 2f, 0.5f);
        for (int t = 0; t < 4; t++) {
            Bukkit.getScheduler().runTaskLater(this, () -> drawRing(center, radius, Particle.SOUL_FIRE_FLAME), t * 5L);
        }
        Bukkit.getScheduler().runTaskLater(this, () -> {
            if (!king.isValid()) return;
            w.playSound(center, Sound.ENTITY_PLAYER_ATTACK_SWEEP, 2f, 0.6f);
            w.spawnParticle(Particle.SWEEP_ATTACK, center.clone().add(0, 1.5, 0), 20, radius / 2, 0.5, radius / 2, 0.2);
            for (Entity e : w.getNearbyEntities(center, radius, 2.5, radius)) {
                if (e instanceof LivingEntity le && !e.equals(king)) {
                    le.damage(12.0, king);
                    le.setVelocity(le.getLocation().toVector().subtract(center.toVector()).normalize().multiply(1.4).setY(0.5));
                }
            }
        }, 20L);
    }

    // Spawns up to 3 skeleton guards (max 6 alive), each despawning after 30s
    private void castSummonCourt(Skeleton king) {
        Set<UUID> guards = bossGuards.computeIfAbsent(king.getUniqueId(), k -> new HashSet<>());
        guards.removeIf(gid -> { Entity g = Bukkit.getEntity(gid); return g == null || !g.isValid(); });
        if (guards.size() >= MAX_GUARDS_ALIVE) return;

        World w = king.getWorld();
        w.playSound(king.getLocation(), Sound.ENTITY_SKELETON_AMBIENT, 2f, 0.7f);
        int toSpawn = Math.min(3, MAX_GUARDS_ALIVE - guards.size());
        for (int i = 0; i < toSpawn; i++) {
            double angle = rng.nextDouble() * Math.PI * 2;
            Location spawnLoc = king.getLocation().clone().add(Math.cos(angle) * 3, 0, Math.sin(angle) * 3);
            Skeleton guard = w.spawn(spawnLoc, Skeleton.class);
            guard.getAttribute(Attribute.MAX_HEALTH).setBaseValue(100);
            guard.setHealth(100);
            guard.setCustomName("§7☠ Royal Guard ☠");
            guard.setCustomNameVisible(true);
            guard.getPersistentDataContainer().set(bossTagKey, PersistentDataType.STRING, "guard");
            guard.getEquipment().setItemInMainHand(new ItemStack(Material.IRON_SWORD));
            guard.getEquipment().setItemInMainHandDropChance(0f);
            guards.add(guard.getUniqueId());
            w.spawnParticle(Particle.SOUL, spawnLoc.clone().add(0, 1, 0), 20, 0.5, 1, 0.5, 0.1);

            UUID gid = guard.getUniqueId();
            UUID kingId = king.getUniqueId();
            Bukkit.getScheduler().runTaskLater(this, () -> {
                Entity g = Bukkit.getEntity(gid);
                if (g != null && g.isValid()) g.remove();
                Set<UUID> set = bossGuards.get(kingId);
                if (set != null) set.remove(gid);
            }, GUARD_LIFETIME_TICKS);
        }
    }

    // Phase 2: telegraphs the target's position, leaps over, and lands for AoE damage + Slowness
    private void castKingsJudgment(Skeleton king, Player target) {
        World w = king.getWorld();
        Location targetLoc = target.getLocation();
        w.playSound(king.getLocation(), Sound.ENTITY_SKELETON_AMBIENT, 2f, 0.4f);
        for (int t = 0; t < 3; t++) {
            Bukkit.getScheduler().runTaskLater(this, () -> drawRing(targetLoc, 4.0, Particle.SMOKE), t * 8L);
        }
        Vector leap = targetLoc.toVector().subtract(king.getLocation().toVector()).normalize().multiply(1.6);
        leap.setY(0.7);
        king.setVelocity(leap);
        Bukkit.getScheduler().runTaskLater(this, () -> {
            if (!king.isValid()) return;
            Location land = king.getLocation();
            w.playSound(land, Sound.ENTITY_GENERIC_EXPLODE, 2f, 0.8f);
            w.spawnParticle(Particle.EXPLOSION_EMITTER, land, 1);
            for (Entity e : w.getNearbyEntities(land, 4, 3, 4)) {
                if (e instanceof LivingEntity le && !e.equals(king)) {
                    le.damage(16.0, king);
                    if (le instanceof Player pl) {
                        pl.addPotionEffect(new PotionEffect(PotionEffectType.SLOWNESS, 60, 1, false, false, true));
                    }
                }
            }
        }, 25L);
    }

    // Keeps each tracked boss's health bar synced and visible only to nearby players
    private void updateBossBars() {
        Iterator<Map.Entry<UUID, BossBar>> it = activeBossBars.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<UUID, BossBar> entry = it.next();
            Entity entity = Bukkit.getEntity(entry.getKey());
            BossBar bar = entry.getValue();

            if (!(entity instanceof LivingEntity boss) || boss.isDead() || !boss.isValid()) {
                bar.removeAll();
                it.remove();
                bossPhaseTwoTriggered.remove(entry.getKey());
                cleanupBoss(entry.getKey());
                ItemDisplay display = bossDisplayModels.remove(entry.getKey());
                if (display != null) display.remove();
                continue;
            }

            double max = boss.getAttribute(Attribute.MAX_HEALTH).getValue();
            double progress = Math.max(0.0, Math.min(1.0, boss.getHealth() / max));
            bar.setProgress(progress);

            // Live HP numbers in the bar title, e.g. "THE ELDER WARDEN [4380/5000❤]"
            String baseTitle = boss instanceof Warden ? "§4§l⚠ THE ELDER WARDEN ⚠" : "§8§l☠ THE CROWNED SKELETON ☠";
            bar.setTitle(baseTitle + " §8[" + (int) Math.ceil(boss.getHealth()) + "§7/" + (int) max + "❤]");

            boolean enraged = progress <= 0.5;
            if (enraged && bossPhaseTwoTriggered.add(boss.getUniqueId())) {
                bar.setColor(BarColor.PURPLE);
                boss.getWorld().spawnParticle(Particle.EXPLOSION, boss.getLocation().add(0, 1.5, 0), 6);
                boss.getWorld().playSound(boss.getLocation(),
                        boss instanceof Warden ? Sound.ENTITY_WARDEN_ROAR : Sound.ENTITY_WITHER_AMBIENT, 2f, 0.7f);
                Bukkit.broadcastMessage((boss instanceof Warden ? "§4§l⚠ " : "§8§l☠ ")
                        + boss.getName() + " §7has entered its §c§lENRAGED§7 phase!");
            }

            // Ambient aura so the mega boss reads differently from a wild spawn at a glance
            if (boss instanceof Warden) {
                boss.getWorld().spawnParticle(Particle.SCULK_SOUL, boss.getLocation().add(0, 1.5, 0), enraged ? 25 : 15, 0.8, 1.2, 0.8, 0.02);
                boss.getWorld().spawnParticle(Particle.WARPED_SPORE, boss.getLocation().add(0, 1.5, 0), enraged ? 18 : 10, 0.8, 1.2, 0.8, 0.01);
                if (enraged) {
                    boss.getWorld().spawnParticle(Particle.REVERSE_PORTAL, boss.getLocation().add(0, 1.5, 0), 12, 0.8, 1.2, 0.8, 0.02);
                }
            } else if (boss instanceof Skeleton) {
                boss.getWorld().spawnParticle(Particle.SOUL_FIRE_FLAME, boss.getLocation().add(0, 1.5, 0), enraged ? 20 : 12, 0.8, 1.2, 0.8, 0.01);
                boss.getWorld().spawnParticle(Particle.SMOKE, boss.getLocation().add(0, 1.5, 0), 8, 0.6, 1.0, 0.6, 0.01);
            }

            for (Player p : boss.getWorld().getPlayers()) {
                boolean inRange = p.getLocation().distanceSquared(boss.getLocation()) <= BOSS_BAR_RADIUS * BOSS_BAR_RADIUS;
                boolean showing = bar.getPlayers().contains(p);
                if (inRange && !showing) {
                    bar.addPlayer(p);
                } else if (!inRange && showing) {
                    bar.removePlayer(p);
                }
            }
        }
    }

    // Boss death drops the corresponding legendary weapon and nothing else
    @EventHandler
    public void onBossDeath(EntityDeathEvent event) {
        String bossType = event.getEntity().getPersistentDataContainer().get(bossTagKey, PersistentDataType.STRING);
        if (bossType == null) return;

        // Guards drop nothing and despawn quietly
        if (bossType.equals("guard")) {
            event.getDrops().clear();
            event.setDroppedExp(0);
            return;
        }

        BossBar bar = activeBossBars.remove(event.getEntity().getUniqueId());
        if (bar != null) bar.removeAll();
        bossPhaseTwoTriggered.remove(event.getEntity().getUniqueId());
        cleanupBoss(event.getEntity().getUniqueId());
        ItemDisplay display = bossDisplayModels.remove(event.getEntity().getUniqueId());
        if (display != null) display.remove();

        event.getDrops().clear();
        event.setDroppedExp(0);

        boolean warden = bossType.equals("warden");
        event.getDrops().add(warden ? createGodSpear() : createGodSword());

        Player killer = event.getEntity().getKiller();
        String killerName = (killer != null) ? killer.getName() : "someone";
        Bukkit.broadcastMessage(warden
                ? "§5§l✦ " + killerName + " has slain §4§lTHE ELDER WARDEN§r§5§l and claimed the §d§lGOD SPEAR§r§5§l! ✦"
                : "§5§l✦ " + killerName + " has slain §8§lTHE CROWNED SKELETON§r§5§l and claimed the §f§lGOD SWORD§r§5§l! ✦");
    }

    private ItemStack createGodSpear() {
        ItemStack spear = new ItemStack(Material.NETHERITE_SPEAR);
        ItemMeta meta = spear.getItemMeta();
        meta.setDisplayName("§5§l✦ GOD SPEAR ✦");
        meta.setUnbreakable(true);
        meta.getPersistentDataContainer().set(legendaryWeaponKey, PersistentDataType.STRING, "spear");
        meta.addEnchant(Enchantment.LUNGE, 4, true);
        meta.addEnchant(Enchantment.SHARPNESS, 7, true);
        meta.addEnchant(Enchantment.UNBREAKING, 7, true);
        meta.addEnchant(Enchantment.MENDING, 1, true);
        meta.addItemFlags(ItemFlag.HIDE_ENCHANTS, ItemFlag.HIDE_UNBREAKABLE);

        List<String> lore = new ArrayList<>();
        lore.add("§7Torn from the depths by the Void Warden itself.");
        lore.add("");
        lore.add("§5§l★ LEGENDARY");
        lore.add("§b§lUnbreakable §7• §fLunge IV, Sharpness VII, Unbreaking VII, Mending");
        lore.add("§6• On-Hit: §f+30 damage, 25% chance to inflict");
        lore.add("  §fDarkness + Sonic Boom shock");
        lore.add("§6• Sneak+Left-Click: §fVoid Pierce §7(dash + line AoE, 6s cd)");
        meta.setLore(lore);

        spear.setItemMeta(meta);
        return spear;
    }

    private ItemStack createGodSword() {
        ItemStack sword = new ItemStack(Material.NETHERITE_SWORD);
        ItemMeta meta = sword.getItemMeta();
        meta.setDisplayName("§f§l✦ GOD SWORD ✦");
        meta.setUnbreakable(true);
        meta.getPersistentDataContainer().set(legendaryWeaponKey, PersistentDataType.STRING, "sword");
        meta.addEnchant(Enchantment.SHARPNESS, 15, true);
        meta.addEnchant(Enchantment.SWEEPING_EDGE, 10, true);
        meta.addEnchant(Enchantment.FIRE_ASPECT, 8, true);
        meta.addEnchant(Enchantment.LOOTING, 10, true);
        meta.addEnchant(Enchantment.UNBREAKING, 10, true);
        meta.addEnchant(Enchantment.MENDING, 1, true);
        meta.addItemFlags(ItemFlag.HIDE_ENCHANTS, ItemFlag.HIDE_UNBREAKABLE);

        List<String> lore = new ArrayList<>();
        lore.add("§7Forged from the bones of the Sovereign's throne.");
        lore.add("");
        lore.add("§5§l★ LEGENDARY");
        lore.add("§b§lUnbreakable §7• §fSharpness XV, Sweeping Edge X,");
        lore.add("  §fFire Aspect VIII, Looting X, Unbreaking X, Mending");
        lore.add("§6• On-Hit: §f+25 damage, 30% chance to rain");
        lore.add("  §f3 arrows down on your target");
        lore.add("§6• Sneak+Right-Click: §fBone Storm §7(AoE arrow rain, 12s cd)");
        meta.setLore(lore);

        sword.setItemMeta(meta);
        return sword;
    }

    private String getLegendaryType(ItemStack item) {
        if (item == null || !item.hasItemMeta()) return null;
        return item.getItemMeta().getPersistentDataContainer().get(legendaryWeaponKey, PersistentDataType.STRING);
    }

    // On-hit passives for the two legendary weapons
    @EventHandler
    public void onLegendaryHit(EntityDamageByEntityEvent event) {
        if (!(event.getDamager() instanceof Player attacker)) return;
        String weapon = getLegendaryType(attacker.getInventory().getItemInMainHand());
        if (weapon == null) return;
        if (!(event.getEntity() instanceof LivingEntity victim)) return;

        if (weapon.equals("spear")) {
            event.setDamage(event.getDamage() + 30.0);
            if (rng.nextDouble() < 0.25) {
                victim.getWorld().spawnParticle(Particle.SONIC_BOOM, victim.getLocation(), 1);
                victim.getWorld().playSound(victim.getLocation(), Sound.ENTITY_WARDEN_SONIC_BOOM, 1f, 1.2f);
                victim.addPotionEffect(new PotionEffect(PotionEffectType.DARKNESS, 100, 0, false, false, true));
                victim.setVelocity(victim.getVelocity().add(new Vector(0, 0.4, 0)));
            }
        } else if (weapon.equals("sword")) {
            event.setDamage(event.getDamage() + 25.0);
            if (rng.nextDouble() < 0.3) {
                for (int i = 0; i < 3; i++) {
                    Location arrowSpawn = victim.getLocation().add((rng.nextDouble() - 0.5) * 3, 6, (rng.nextDouble() - 0.5) * 3);
                    Arrow arrow = victim.getWorld().spawn(arrowSpawn, Arrow.class);
                    arrow.setVelocity(new Vector(0, -1.2, 0));
                    arrow.setShooter(attacker);
                    arrow.setDamage(6.0);
                }
            }
        }
    }

    // Spear active: Void Pierce — sneak + left-click
    @EventHandler
    public void onSpearAbility(PlayerInteractEvent event) {
        Player player = event.getPlayer();
        if (!"spear".equals(getLegendaryType(player.getInventory().getItemInMainHand()))) return;
        if (!player.isSneaking()) return;
        if (event.getAction() != Action.LEFT_CLICK_AIR && event.getAction() != Action.LEFT_CLICK_BLOCK) return;

        UUID uuid = player.getUniqueId();
        long now = System.currentTimeMillis();
        Long cd = spearCooldownEnd.get(uuid);
        if (cd != null && cd > now) {
            player.sendMessage("§cVoid Pierce is on cooldown for " + String.format("%.1f", (cd - now) / 1000.0) + "s.");
            return;
        }
        spearCooldownEnd.put(uuid, now + SPEAR_COOLDOWN_MS);

        Location start = player.getEyeLocation();
        Vector dir = start.getDirection().normalize();
        for (double d = 0; d <= 8.0; d += 0.5) {
            Location point = start.clone().add(dir.clone().multiply(d));
            for (Entity nearby : point.getWorld().getNearbyEntities(point, 1.2, 1.2, 1.2)) {
                if (nearby instanceof LivingEntity target && !nearby.equals(player)) {
                    target.damage(15.0, player);
                    target.addPotionEffect(new PotionEffect(PotionEffectType.DARKNESS, 60, 0, false, false, true));
                }
            }
        }
        Vector dash = dir.clone().multiply(2.2);
        dash.setY(0.3);
        player.setVelocity(dash);
        player.getWorld().spawnParticle(Particle.SONIC_BOOM, start, 1);
        player.getWorld().playSound(start, Sound.ENTITY_WARDEN_SONIC_BOOM, 1.5f, 1f);
        player.sendMessage("§5§l⚡ VOID PIERCE! §7You tore through reality.");
    }

    // Sword active: Bone Storm — sneak + right-click
    @EventHandler
    public void onSwordAbility(PlayerInteractEvent event) {
        Player player = event.getPlayer();
        if (!"sword".equals(getLegendaryType(player.getInventory().getItemInMainHand()))) return;
        if (!player.isSneaking()) return;
        if (event.getAction() != Action.RIGHT_CLICK_AIR && event.getAction() != Action.RIGHT_CLICK_BLOCK) return;

        UUID uuid = player.getUniqueId();
        long now = System.currentTimeMillis();
        Long cd = swordCooldownEnd.get(uuid);
        if (cd != null && cd > now) {
            player.sendMessage("§cBone Storm is on cooldown for " + String.format("%.1f", (cd - now) / 1000.0) + "s.");
            return;
        }
        swordCooldownEnd.put(uuid, now + SWORD_COOLDOWN_MS);

        var targetBlock = player.getTargetBlockExact(20);
        Location center = (targetBlock != null) ? targetBlock.getLocation().add(0.5, 1, 0.5) : player.getLocation();
        player.sendMessage("§7§l☠ BONE STORM SUMMONED! §7Arrows rain from above.");
        for (int i = 0; i < 12; i++) {
            Bukkit.getScheduler().runTaskLater(this, () -> {
                double ox = (rng.nextDouble() - 0.5) * 6;
                double oz = (rng.nextDouble() - 0.5) * 6;
                Location spawnLoc = center.clone().add(ox, 6, oz);
                Arrow arrow = center.getWorld().spawn(spawnLoc, Arrow.class);
                arrow.setVelocity(new Vector(0, -1.4, 0));
                arrow.setShooter(player);
                arrow.setDamage(9.0);
            }, i * 3L);
        }
        player.getWorld().playSound(center, Sound.ENTITY_SKELETON_AMBIENT, 2f, 0.6f);
    }

    private boolean isGodArmorPiece(ItemStack item) {
        if (item == null || !item.hasItemMeta()) return false;
        return item.getItemMeta().getPersistentDataContainer().has(godArmorKey, PersistentDataType.BYTE);
    }

    // If ANY player equips a Crown (picked up, traded, whatever) and is missing other pieces,
    // the Crown grants the rest of the God Armor set — this is how a random finder of a dropped
    // Crown ends up with the full set, same as the original crafter.
    @EventHandler
    public void onEquipCrown(PlayerArmorChangeEvent event) {
        if (event.getSlot() != EquipmentSlot.HEAD) return;
        ItemStack newItem = event.getNewItem();
        if (newItem == null || newItem.getType() != Material.NETHERITE_HELMET) return;
        if (!isGodArmorPiece(newItem)) return;

        Player player = event.getPlayer();
        Bukkit.getScheduler().runTask(this, () -> {
            PlayerInventory inv = player.getInventory();
            List<ItemStack> toGive = new ArrayList<>();
            if (!isGodArmorPiece(inv.getChestplate())) {
                toGive.add(createGodArmorPiece(Material.NETHERITE_CHESTPLATE, "§6§l✧ CHESTPLATE OF THE GODS ✧", "Chestplate"));
            }
            if (!isGodArmorPiece(inv.getLeggings())) {
                toGive.add(createGodArmorPiece(Material.NETHERITE_LEGGINGS, "§6§l✧ LEGGINGS OF THE GODS ✧", "Leggings"));
            }
            if (!isGodArmorPiece(inv.getBoots())) {
                toGive.add(createGodArmorPiece(Material.NETHERITE_BOOTS, "§6§l✧ BOOTS OF THE GODS ✧", "Boots"));
            }
            if (!toGive.isEmpty()) {
                inv.addItem(toGive.toArray(new ItemStack[0]));
                player.playSound(player.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1f, 0.7f);
                player.getWorld().spawnParticle(Particle.TOTEM_OF_UNDYING, player.getLocation().add(0, 1, 0), 40, 0.5, 1, 0.5, 0.3);
                player.sendMessage("§6§l✧ §fThe Crown recognizes you as its bearer — the rest of the §6§lGOD ARMOR §fset is bestowed!");
            }
        });
    }

    // --- BANISH ABILITY (Godly Mace only, permission-gated) ---
    // Sneak + right-click a player with a 15+ kill mace to banish them from the server.
    @EventHandler
    public void onBanishAbility(PlayerInteractEntityEvent event) {
        if (event.getHand() != EquipmentSlot.HAND) return; // avoid double-firing from off-hand
        if (!(event.getRightClicked() instanceof Player target)) return;

        Player attacker = event.getPlayer();
        if (!attacker.isSneaking()) return;

        ItemStack mace = attacker.getInventory().getItemInMainHand();
        if (getMaceKills(mace) < 15) return; // Godly tier only

        if (!attacker.hasPermission(BAN_PERMISSION)) {
            attacker.sendMessage("§cYou don't have permission to use the God Mace's banishment.");
            return;
        }

        event.setCancelled(true);
        String reason = "§d§lBanished by the God Mace, wielded by " + attacker.getName();
        target.banPlayer(reason);
        target.kickPlayer(reason);

        Bukkit.broadcastMessage("§4§l⚡ " + target.getName() + " has been BANISHED by " + attacker.getName() + "'s God Mace! ⚡");
        attacker.getWorld().spawnParticle(Particle.SOUL, target.getLocation(), 60, 0.5, 1, 0.5, 0.15);
        attacker.playSound(attacker.getLocation(), Sound.ENTITY_WITHER_DEATH, 1f, 1f);
    }

    // --- SECOND WIND (Full God Armor set only) ---
    // Emergency heal + absorption when a wearer drops critically low, on a cooldown.
    @EventHandler(priority = org.bukkit.event.EventPriority.MONITOR)
    public void onSecondWind(EntityDamageEvent event) {
        if (event.isCancelled()) return;
        if (!(event.getEntity() instanceof Player p)) return;
        if (!isWearingFullGodArmor(p)) return;

        double resultingHealth = p.getHealth() - event.getFinalDamage();
        if (resultingHealth <= 0) return; // don't interfere with an actual death
        if (resultingHealth > p.getMaxHealth() * 0.2) return; // only trigger below 20% HP

        UUID uuid = p.getUniqueId();
        long now = System.currentTimeMillis();
        Long cooldownEnd = secondWindCooldown.get(uuid);
        if (cooldownEnd != null && cooldownEnd > now) return;
        secondWindCooldown.put(uuid, now + SECOND_WIND_COOLDOWN_MS);

        // Apply a tick later so it doesn't interfere with resolving the current damage event
        Bukkit.getScheduler().runTask(this, () -> {
            p.setHealth(Math.min(p.getMaxHealth(), p.getHealth() + p.getMaxHealth() * 0.5));
            p.addPotionEffect(new PotionEffect(PotionEffectType.ABSORPTION, 200, 1, false, true, true));
            p.addPotionEffect(new PotionEffect(PotionEffectType.REGENERATION, 100, 2, false, true, true));
            p.getWorld().spawnParticle(Particle.TOTEM_OF_UNDYING, p.getLocation().add(0, 1, 0), 50, 0.5, 1, 0.5, 0.3);
            p.playSound(p.getLocation(), Sound.ITEM_TOTEM_USE, 1f, 1f);
            p.sendMessage("§6§l✧ SECOND WIND! §fThe God Armor shields you from death's door. §7(3 min cooldown)");
        });
    }

    @Override
    public boolean onCommand(CommandSender sender, Command cmd, String label, String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("Players only.");
            return true;
        }
        if (!player.hasPermission("godmace.admin")) {
            player.sendMessage("§cNo permission.");
            return true;
        }

        if (args.length == 0) {
            sendHelp(player);
            return true;
        }

        switch (args[0].toLowerCase()) {
            case "mace" -> {
                int kills = 0;
                if (args.length >= 2) {
                    try {
                        kills = Math.max(0, Integer.parseInt(args[1]));
                    } catch (NumberFormatException ignored) {
                        player.sendMessage("§cKills must be a number, e.g. /getgodmace mace 15");
                        return true;
                    }
                }
                player.getInventory().addItem(createFreshMace(kills));
                player.sendMessage("§aGave a mace at " + kills + " kills.");
            }
            case "crown" -> give(player, createGodArmorPiece(Material.NETHERITE_HELMET, "§6§l✧ CROWN OF THE GODS ✧", "Helmet"), "Crown of the Gods");
            case "chestplate" -> give(player, createGodArmorPiece(Material.NETHERITE_CHESTPLATE, "§6§l✧ CHESTPLATE OF THE GODS ✧", "Chestplate"), "Chestplate of the Gods");
            case "leggings" -> give(player, createGodArmorPiece(Material.NETHERITE_LEGGINGS, "§6§l✧ LEGGINGS OF THE GODS ✧", "Leggings"), "Leggings of the Gods");
            case "boots" -> give(player, createGodArmorPiece(Material.NETHERITE_BOOTS, "§6§l✧ BOOTS OF THE GODS ✧", "Boots"), "Boots of the Gods");
            case "armor", "armour" -> {
                player.getInventory().addItem(
                        createGodArmorPiece(Material.NETHERITE_HELMET, "§6§l✧ CROWN OF THE GODS ✧", "Helmet"),
                        createGodArmorPiece(Material.NETHERITE_CHESTPLATE, "§6§l✧ CHESTPLATE OF THE GODS ✧", "Chestplate"),
                        createGodArmorPiece(Material.NETHERITE_LEGGINGS, "§6§l✧ LEGGINGS OF THE GODS ✧", "Leggings"),
                        createGodArmorPiece(Material.NETHERITE_BOOTS, "§6§l✧ BOOTS OF THE GODS ✧", "Boots")
                );
                player.sendMessage("§aGave the full God Armor set.");
            }
            case "spear" -> give(player, createGodSpear(), "God Spear");
            case "sword" -> give(player, createGodSword(), "God Sword");
            case "mapwarden" -> give(player, createTreasureMap("warden", player.getLocation()), "Warden Treasure Map");
            case "mapskeleton" -> give(player, createTreasureMap("skeleton", player.getLocation()), "Skeleton Treasure Map");
            case "spawnwarden" -> {
                spawnWardenBoss(player.getLocation());
                player.sendMessage("§aSpawned the Void Warden boss at your location.");
            }
            case "spawnskeleton" -> {
                spawnSkeletonBoss(player.getLocation());
                player.sendMessage("§aSpawned the Bone Sovereign boss at your location.");
            }
            case "all" -> {
                player.getInventory().addItem(
                        createFreshMace(15),
                        createGodArmorPiece(Material.NETHERITE_HELMET, "§6§l✧ CROWN OF THE GODS ✧", "Helmet"),
                        createGodArmorPiece(Material.NETHERITE_CHESTPLATE, "§6§l✧ CHESTPLATE OF THE GODS ✧", "Chestplate"),
                        createGodArmorPiece(Material.NETHERITE_LEGGINGS, "§6§l✧ LEGGINGS OF THE GODS ✧", "Leggings"),
                        createGodArmorPiece(Material.NETHERITE_BOOTS, "§6§l✧ BOOTS OF THE GODS ✧", "Boots"),
                        createGodSpear(),
                        createGodSword()
                );
                player.sendMessage("§aGave every item: Godly Mace, full God Armor, God Spear, God Sword.");
            }
            default -> sendHelp(player);
        }
        return true;
    }

    private void give(Player player, ItemStack item, String label) {
        player.getInventory().addItem(item);
        player.sendMessage("§aGave " + label + ".");
    }

    private void sendHelp(Player player) {
        player.sendMessage("§6§l--- GodMace Test Commands ---");
        player.sendMessage("§e/getgodmace mace [kills] §7- Mace at tier (0/6/15), default 0");
        player.sendMessage("§e/getgodmace crown §7- Crown of the Gods only");
        player.sendMessage("§e/getgodmace chestplate|leggings|boots §7- Single armor piece");
        player.sendMessage("§e/getgodmace armor §7- Full 4-piece God Armor set");
        player.sendMessage("§e/getgodmace spear §7- God Spear");
        player.sendMessage("§e/getgodmace sword §7- God Sword");
        player.sendMessage("§e/getgodmace mapwarden|mapskeleton §7- Treasure map to a boss");
        player.sendMessage("§e/getgodmace spawnwarden|spawnskeleton §7- Spawn boss at your location");
        player.sendMessage("§e/getgodmace all §7- One of everything");
    }

    // --- EVOLUTION MECHANIC (Kills Upgrade Weapon) ---
    @EventHandler
    public void onPlayerKill(PlayerDeathEvent event) {
        Player victim = event.getEntity();
        Player killer = victim.getKiller();
        if (killer == null) return;

        ItemStack mace = killer.getInventory().getItemInMainHand();
        int currentKills = getMaceKills(mace);
        if (currentKills == -1) return; // Not a custom plugin mace

        int newKills = currentKills + 1;
        killer.getInventory().setItemInMainHand(createFreshMace(newKills));

        killer.playSound(killer.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1f, 1f);
        killer.sendMessage("§d§l⚡ MACE UPGRADED! §eLevel: " + newKills + "/15");
    }

    // --- RESET MECHANIC (Losing weapon progress on death) ---
    @EventHandler
    public void onPlayerDeath(PlayerDeathEvent event) {
        Player player = event.getEntity();
        ListIterator<ItemStack> iterator = event.getDrops().listIterator();
        while (iterator.hasNext()) {
            ItemStack drop = iterator.next();
            if (getMaceKills(drop) >= 0) {
                iterator.remove(); // Cleanly remove instead of leaving an AIR stack behind
                player.sendMessage("§cYour custom mace shattered and reset upon death!");
            }
        }
        // Dying breaks your combo/dash state entirely
        resetCombo(player.getUniqueId());
        fallImmunity.remove(player.getUniqueId());
    }

    // Combo resets if you take damage from someone else — punishes trading instead of dodging
    @EventHandler
    public void onAttackerTakesDamage(EntityDamageByEntityEvent event) {
        if (event.getEntity() instanceof Player victim && event.getDamager() instanceof Player) {
            if (comboCount.containsKey(victim.getUniqueId())) {
                resetCombo(victim.getUniqueId());
            }
        }
    }

    // --- GIVE STARTER MACE ON JOIN ---
    @EventHandler
    public void onPlayerJoin(PlayerJoinEvent event) {
        Player player = event.getPlayer();
        if (!hasCustomMace(player)) {
            player.getInventory().addItem(createFreshMace(0));
            player.sendMessage("§d§l[GodMace] §aYou've been given a Starter Mace! Get player kills to evolve it.");
        }
    }

    private boolean hasCustomMace(Player player) {
        for (ItemStack item : player.getInventory().getContents()) {
            if (getMaceKills(item) >= 0) return true;
        }
        return false;
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        UUID uuid = event.getPlayer().getUniqueId();
        dashCooldownEnd.remove(uuid);
        fallImmunity.remove(uuid);
        comboCount.remove(uuid);
        lastHitTime.remove(uuid);
    }

    // --- DASH ABILITY (Shift + Left Click) ---
    @EventHandler
    public void onLeftClick(PlayerInteractEvent event) {
        Player player = event.getPlayer();
        ItemStack item = player.getInventory().getItemInMainHand();
        int kills = getMaceKills(item);

        if (kills < 6) return; // Unlocks at 6 kills
        if (!player.isSneaking()) return;
        if (event.getAction() != Action.LEFT_CLICK_AIR && event.getAction() != Action.LEFT_CLICK_BLOCK) return;

        UUID uuid = player.getUniqueId();
        long now = System.currentTimeMillis();
        Long cooldownEnd = dashCooldownEnd.get(uuid);
        if (cooldownEnd != null && cooldownEnd > now) {
            double remaining = (cooldownEnd - now) / 1000.0;
            player.sendMessage("§cDash is on cooldown for " + String.format("%.1f", remaining) + "s.");
            return;
        }

        dashCooldownEnd.put(uuid, now + getDashCooldownMs(kills));
        fallImmunity.add(uuid);

        player.getWorld().playSound(player.getLocation(), Sound.ENTITY_WIND_CHARGE_THROW, 2.0f, 0.5f);
        player.getWorld().playSound(player.getLocation(), Sound.ENTITY_WARDEN_SONIC_BOOM, 1.0f, 1.2f);
        player.getWorld().spawnParticle(Particle.GUST, player.getLocation(), 5);

        Vector v = player.getLocation().getDirection().multiply(2.5).setY(0.4);
        player.setVelocity(v);
    }

    // --- COMBAT ATTACKS (Crits, Combos, Smite & AoE Shockwave) ---
    @EventHandler
    public void onMaceHit(EntityDamageByEntityEvent event) {
        if (event.getCause() == EntityDamageEvent.DamageCause.LIGHTNING) return;
        if (!(event.getDamager() instanceof Player attacker)) return;
        if (smiteInProgress.contains(attacker.getUniqueId())) return; // re-entrant shockwave hit, ignore

        ItemStack mace = attacker.getInventory().getItemInMainHand();
        int kills = getMaceKills(mace);
        if (kills < 0) return;

        LivingEntity victim = (LivingEntity) event.getEntity();
        UUID uuid = attacker.getUniqueId();
        double bonusDamage = 0;

        // --- Combo tracking ---
        long now = System.currentTimeMillis();
        Long last = lastHitTime.get(uuid);
        int combo = (last != null && (now - last) <= COMBO_WINDOW_MS) ? comboCount.getOrDefault(uuid, 0) + 1 : 1;
        combo = Math.min(combo, MAX_COMBO);
        comboCount.put(uuid, combo);
        lastHitTime.put(uuid, now);

        if (combo >= 3) {
            double comboBonus = combo * COMBO_DAMAGE_PER_STACK;
            bonusDamage += comboBonus;
            attacker.sendActionBar(ChatColor.YELLOW + "Combo x" + combo + ChatColor.GRAY + "  (+"
                    + String.format("%.1f", comboBonus) + " dmg)");

            // Every 5-combo shaves a second off the current dash cooldown
            if (combo % 5 == 0 && dashCooldownEnd.containsKey(uuid)) {
                long reduced = Math.max(now, dashCooldownEnd.get(uuid) - 1000);
                dashCooldownEnd.put(uuid, reduced);
                attacker.sendMessage("§b§l[Combo] §fDash cooldown reduced!");
            }
        }

        // --- Crit roll (chance scales with tier) ---
        boolean isCrit = rng.nextDouble() < getCritChance(kills);

        // Tier 3: God Mace Lightning Smite (15 Kills)
        if (kills >= 15) {
            victim.getWorld().strikeLightningEffect(victim.getLocation());
            bonusDamage += 20.0;

            // Radial Ground Shockwave — guarded against re-triggering onMaceHit recursively
            smiteInProgress.add(uuid);
            try {
                for (Entity nearby : victim.getNearbyEntities(4, 3, 4)) {
                    if (nearby instanceof LivingEntity target && !nearby.equals(attacker) && !nearby.equals(victim)) {
                        target.damage(8.0, attacker);
                        target.setVelocity(new Vector(0, 0.5, 0));
                    }
                }
            } finally {
                smiteInProgress.remove(uuid);
            }
            victim.getWorld().spawnParticle(Particle.EXPLOSION, victim.getLocation(), 3);
            victim.getWorld().playSound(victim.getLocation(), Sound.ENTITY_LIGHTNING_BOLT_THUNDER, 1f, 0.8f);
        }
        // Tier 2: Mid tier damage additions
        else if (kills >= 6) {
            bonusDamage += 8.0;
        }

        if (isCrit) {
            double critDamage = (event.getDamage() + bonusDamage) * 0.5; // +50% on top of everything else
            bonusDamage += critDamage;
            victim.getWorld().spawnParticle(Particle.CRIT, victim.getLocation().add(0, 1, 0), 25, 0.3, 0.3, 0.3, 0.2);
            victim.getWorld().playSound(victim.getLocation(), Sound.ENTITY_PLAYER_ATTACK_CRIT, 1f, 1f);
            attacker.sendMessage("§c§lCRITICAL HIT! §7(+50% damage)");
        }

        // --- Execute (Godly tier): guarantees a kill on already-low-health targets ---
        boolean executed = false;
        if (kills >= 15 && victim.getHealth() <= victim.getMaxHealth() * 0.2) {
            bonusDamage += victim.getHealth() + 50; // lethal regardless of remaining armor/resistance
            executed = true;
        }

        event.setDamage(event.getDamage() + bonusDamage);

        if (executed) {
            victim.getWorld().spawnParticle(Particle.SOUL_FIRE_FLAME, victim.getLocation(), 30, 0.3, 0.5, 0.3, 0.1);
            victim.getWorld().playSound(victim.getLocation(), Sound.ENTITY_WITHER_HURT, 1f, 0.6f);
            attacker.sendMessage("§4§l☠ EXECUTED! §7Target was finished off.");
        }

        // --- Heart Steal & Withered Effect (PvP only) ---
        if (victim instanceof Player) {
            double totalDamage = event.getDamage();

            double healAmount = totalDamage * getLifestealPercent(kills);
            double maxHealth = attacker.getAttribute(org.bukkit.attribute.Attribute.MAX_HEALTH).getValue();
            double newHealth = Math.min(maxHealth, attacker.getHealth() + healAmount);
            attacker.setHealth(newHealth);

            attacker.getWorld().spawnParticle(Particle.HEART, attacker.getLocation().add(0, 1.5, 0), 6, 0.3, 0.3, 0.3, 0);
            attacker.sendActionBar(ChatColor.RED + "+" + String.format("%.1f", healAmount) + " ♥ stolen");

            int witherDuration = getWitherDurationTicks(kills);
            if (witherDuration > 0) {
                int witherLevel = (kills >= 15) ? 1 : 0; // Level II at Godly tier
                victim.addPotionEffect(new PotionEffect(PotionEffectType.WITHER, witherDuration, witherLevel, false, true, true));
            }
        }

        if (kills >= 15) {
            attacker.sendMessage("§d§l⚡ SMITE! §7You struck your target with pure cosmic energy.");
        }
    }

    private double getLifestealPercent(int kills) {
        if (kills >= 15) return 0.35;
        if (kills >= 6) return 0.20;
        return 0.10;
    }

    private int getWitherDurationTicks(int kills) {
        if (kills >= 15) return 80; // 4s
        if (kills >= 6) return 60;  // 3s
        return 40;                 // 2s
    }

    @EventHandler
    public void onFallDamage(EntityDamageEvent event) {
        if (event.getEntity() instanceof Player p && event.getCause() == EntityDamageEvent.DamageCause.FALL) {
            if (isWearingFullGodArmor(p) || fallImmunity.contains(p.getUniqueId())) {
                event.setCancelled(true);
                fallImmunity.remove(p.getUniqueId());
            }
        }
    }

    private void resetCombo(UUID uuid) {
        comboCount.remove(uuid);
        lastHitTime.remove(uuid);
    }

    private long getDashCooldownMs(int kills) {
        if (kills >= 15) return 1500;
        if (kills >= 6) return 2500;
        return 4000;
    }

    private double getCritChance(int kills) {
        if (kills >= 15) return 0.30;
        if (kills >= 6) return 0.15;
        return 0.05;
    }

    // --- ITEM STRUCTURE BUILDER ---
    private ItemStack createFreshMace(int kills) {
        ItemStack mace = new ItemStack(Material.MACE);
        ItemMeta meta = mace.getItemMeta();
        if (meta == null) return mace;

        meta.getPersistentDataContainer().set(maceLevelKey, PersistentDataType.INTEGER, kills);
        meta.addItemFlags(ItemFlag.HIDE_ENCHANTS);

        List<String> lore = new ArrayList<>();
        lore.add("§7Kills Tracked: §e" + kills + "/15");
        lore.add("");

        if (kills >= 15) {
            meta.setDisplayName("§d§k!§d§l GOD MACE §d§k!");
            meta.addEnchant(Enchantment.DENSITY, 5, true);
            meta.addEnchant(Enchantment.BREACH, 4, true);
            meta.addEnchant(Enchantment.WIND_BURST, 3, true);
            lore.add("§5§l★ TIER: GODLY");
            lore.add("§6• Passive: §fSpeed II, Strength II, Resistance I");
            lore.add("§6• Shift+Left-Click: §fSonic Wind Dash §7(1.5s cd)");
            lore.add("§6• Attack: §fAoE Smashes & Lightning Smites");
            lore.add("§6• Crit Chance: §f30%");
            lore.add("§6• Combo: §f+1.5 dmg/stack §7(3s window, max x10)");
            lore.add("§6• vs Players: §f35% Lifesteal, Wither II §7(4s)");
            lore.add("§6• Execute: §fFinishes targets below 20% HP");
            lore.add("§6• Sneak+Right-Click Player: §fBanish §7(permission-gated)");
        } else if (kills >= 6) {
            meta.setDisplayName("§b§lAdvanced Shockwave Mace");
            meta.addEnchant(Enchantment.DENSITY, 3, true);
            meta.addEnchant(Enchantment.WIND_BURST, 1, true);
            lore.add("§3§l★ TIER: ELITE");
            lore.add("§6• Shift+Left-Click: §fSonic Wind Dash §7(2.5s cd)");
            lore.add("§6• Attack: §f+8 Bonus Pure Weapon Damage");
            lore.add("§6• Crit Chance: §f15%");
            lore.add("§6• Combo: §f+1.5 dmg/stack §7(3s window, max x10)");
            lore.add("§6• vs Players: §f20% Lifesteal, Wither I §7(3s)");
        } else {
            meta.setDisplayName("§eStarter Mace");
            lore.add("§8§l★ TIER: SCRAP");
            lore.add("§7Get 6 player kills to unlock the Dash ability.");
            lore.add("§6• Crit Chance: §f5%");
            lore.add("§6• vs Players: §f10% Lifesteal, Wither I §7(2s)");
        }

        meta.setLore(lore);
        mace.setItemMeta(meta);
        return mace;
    }

    private int getMaceKills(ItemStack item) {
        if (item == null || !item.hasItemMeta()) return -1;
        Integer kills = item.getItemMeta().getPersistentDataContainer().get(maceLevelKey, PersistentDataType.INTEGER);
        return (kills == null) ? -1 : kills;
    }
}