import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

const CATEGORIES = [
  { name: "Audio", slug: "audio" },
  { name: "Wearables", slug: "wearables" },
  { name: "Desk Setup", slug: "desk-setup" },
  { name: "Backpacks", slug: "backpacks" },
];

const PRODUCTS: Array<{
  name: string;
  description: string;
  price: number;
  stock: number;
  category: string;
  imageUrl: string;
}> = [
  {
    name: "PulseBass ANC Headphones",
    description: "Over-ear noise-cancelling headphones with a neon-tuned soundstage and 40h battery.",
    price: 12999,
    stock: 24,
    category: "audio",
    imageUrl: "/products/pulsebass-anc-headphones.jpg",
  },
  {
    name: "GridBeam Smart Speaker",
    description: "360° RGB-lit speaker that reacts to the beat. Voice-ready, Bluetooth 5.3.",
    price: 7999,
    stock: 15,
    category: "audio",
    imageUrl: "/products/gridbeam-smart-speaker.jpg",
  },
  {
    name: "EchoChip In-Ear Buds",
    description: "Wireless earbuds with low-latency gaming mode and a transparent charging case.",
    price: 5999,
    stock: 0,
    category: "audio",
    imageUrl: "/products/echochip-earbuds.jpg",
  },
  {
    name: "Pulse Watch X1",
    description: "AMOLED smartwatch with heart-rate tracking, GPS, and 7-day battery life.",
    price: 14999,
    stock: 9,
    category: "wearables",
    imageUrl: "/products/pulse-watch-x1.jpg",
  },
  {
    name: "NeonBand Fitness Strap",
    description: "Lightweight activity band with sleep tracking and a bright always-on display.",
    price: 4499,
    stock: 40,
    category: "wearables",
    imageUrl: "/products/neonband-fitness-strap.jpg",
  },
  {
    name: "VoltKey 75 Keyboard",
    description: "Hot-swappable 75% mechanical keyboard with per-key RGB and gasket mount.",
    price: 10999,
    stock: 12,
    category: "desk-setup",
    imageUrl: "/products/voltkey-75-keyboard.jpg",
  },
  {
    name: "Photon Mouse Pro",
    description: "8K polling-rate wireless gaming mouse with a 58g honeycomb shell.",
    price: 6999,
    stock: 30,
    category: "desk-setup",
    imageUrl: "/products/photon-mouse-pro.jpg",
  },
  {
    name: "Aurora Desk Light Bar",
    description: "Monitor light bar with adjustable color temperature and no-glare lens.",
    price: 4999,
    stock: 18,
    category: "desk-setup",
    imageUrl: "/products/aurora-desk-light.jpg",
  },
  {
    name: "Circuit Backpack",
    description: "Weatherproof 22L backpack with a padded 16\" laptop sleeve and USB port.",
    price: 8999,
    stock: 8,
    category: "backpacks",
    imageUrl: "/products/circuit-backpack.jpg",
  },
  {
    name: "Grid Runner Sling",
    description: "Compact crossbody sling with RFID-blocking pockets and reflective trim.",
    price: 3499,
    stock: 26,
    category: "backpacks",
    imageUrl: "/products/grid-runner-sling.jpg",
  },
];

const QA_USERS = [
  {
    email: "otp@clickbound.com",
    password: "OtpGrid1!",
    name: "OTP Tester",
    phone: "+1 555 010 0101",
    phoneVerified: true,
  },
  {
    email: "legacy@clickbound.com",
    password: "LegacyGrid1!",
    name: "Legacy Tester",
    phone: null,
    phoneVerified: false,
  },
];

async function seedUsers() {
  for (const u of QA_USERS) {
    const hashed = await bcrypt.hash(u.password, 10);
    await prisma.user.upsert({
      where: { email: u.email },
      update: {},
      create: {
        email: u.email,
        password: hashed,
        name: u.name,
        phone: u.phone,
        emailVerifiedAt: new Date(),
        phoneVerifiedAt: u.phoneVerified ? new Date() : null,
        cart: { create: {} },
      },
    });
    console.log(`User: ${u.email}`);
  }
}

async function main() {
  await seedUsers();

  const existing = await prisma.product.count();
  if (existing > 0) {
    console.log(`Seed skipped — ${existing} products already exist.`);
    return;
  }

  const created = new Map<string, string>();
  for (const c of CATEGORIES) {
    const row = await prisma.category.create({ data: c });
    created.set(c.slug, row.id);
    console.log(`Category: ${c.name}`);
  }

  for (const p of PRODUCTS) {
    await prisma.product.create({
      data: {
        name: p.name,
        description: p.description,
        price: p.price,
        stock: p.stock,
        imageUrl: p.imageUrl,
        categoryId: created.get(p.category) ?? null,
      },
    });
    console.log(`Product: ${p.name}`);
  }

  console.log(`Seeded ${CATEGORIES.length} categories and ${PRODUCTS.length} products.`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
