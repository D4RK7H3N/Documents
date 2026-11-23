import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import {
  ACCESS_TOKEN_MAX_AGE_SECONDS,
  REFRESH_TOKEN_MAX_AGE_SECONDS,
  generateRefreshToken,
  hashPassword,
  hashRefreshToken,
  signToken,
} from "@/lib/auth";
import { verifyProof } from "@/lib/otp";
import { checkRateLimit, rateLimitKey } from "@/lib/rate-limit";

const registerSchema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
  password: z.string().min(8),
  phone: z.string().trim().min(8).max(30),
  emailProof: z.string(),
  phoneProof: z.string(),
});

export async function POST(req: Request) {
  const rate = checkRateLimit(`register:${rateLimitKey(req)}`, 5, 15 * 60 * 1000);
  if (!rate.allowed) {
    return NextResponse.json(
      { error: "Too many attempts. Try again later." },
      { status: 429, headers: { "Retry-After": String(Math.ceil((rate.retryAfterMs ?? 0) / 1000)) } },
    );
  }

  const body = await req.json();
  const parsed = registerSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }

  const { name, email, password } = parsed.data;
  const phone = parsed.data.phone;
  const emailLower = email.toLowerCase();

  const emailProof = verifyProof(parsed.data.emailProof, "email-proof");
  if (!emailProof || emailProof.email !== emailLower) {
    return NextResponse.json({ error: "Email address not verified" }, { status: 400 });
  }

  const phoneProof = verifyProof(parsed.data.phoneProof, "phone-proof");
  if (!phoneProof || phoneProof.phone !== phone) {
    return NextResponse.json({ error: "Phone number not verified" }, { status: 400 });
  }

  const existing = await prisma.user.findUnique({ where: { email: emailLower } });
  if (existing) {
    return NextResponse.json({ error: "Email already registered" }, { status: 409 });
  }

  const phoneTaken = await prisma.user.findFirst({ where: { phone } });
  if (phoneTaken) {
    return NextResponse.json({ error: "Phone already registered" }, { status: 409 });
  }

  const hashed = await hashPassword(password);

  const user = await prisma.user.create({
    data: {
      name,
      email: emailLower,
      password: hashed,
      phone,
      emailVerifiedAt: new Date(),
      phoneVerifiedAt: new Date(),
    },
  });

  // every new user gets an empty cart
  await prisma.cart.create({ data: { userId: user.id } });

  const accessToken = signToken({ userId: user.id, email: user.email, role: user.role });
  const refreshToken = generateRefreshToken();
  await prisma.refreshToken.create({
    data: {
      userId: user.id,
      tokenHash: hashRefreshToken(refreshToken),
      expiresAt: new Date(Date.now() + REFRESH_TOKEN_MAX_AGE_SECONDS * 1000),
    },
  });

  const res = NextResponse.json({
    user: { id: user.id, name: user.name, email: user.email, role: user.role },
  });
  res.cookies.set("token", accessToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS,
    path: "/",
  });
  res.cookies.set("refreshToken", refreshToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS,
    path: "/api/auth",
  });
  return res;
}