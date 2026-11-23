import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import {
  ACCESS_TOKEN_MAX_AGE_SECONDS,
  REFRESH_TOKEN_MAX_AGE_SECONDS,
  generateRefreshToken,
  getTokenFromRequest,
  hashRefreshToken,
  signToken,
  verifyPasswordConstantTime,
} from "@/lib/auth";
import {
  activeOtpCode,
  challengeToken,
  issueOtpCode,
  maskFor,
  verifyTrustedDevice,
} from "@/lib/otp";
import { checkRateLimit, rateLimitKey } from "@/lib/rate-limit";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export async function POST(req: Request) {
  const rate = checkRateLimit(`login:${rateLimitKey(req)}`, 10, 5 * 60 * 1000);
  if (!rate.allowed) {
    return NextResponse.json(
      { error: "Too many attempts. Try again later." },
      { status: 429, headers: { "Retry-After": String(Math.ceil((rate.retryAfterMs ?? 0) / 1000)) } },
    );
  }

  const body = await req.json();
  const parsed = loginSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }

  const { email, password } = parsed.data;

  const user = await prisma.user.findUnique({ where: { email: email.toLowerCase() } });

  if (user && user.lockedUntil && user.lockedUntil.getTime() > Date.now()) {
    return NextResponse.json(
      { error: "Too many failed attempts. Try again later." },
      { status: 423 },
    );
  }

  const valid = await verifyPasswordConstantTime(password, user?.password ?? null);
  if (!valid) {
    if (user) {
      const next = user.failedLoginAttempts + 1;
      if (next >= 5) {
        await prisma.user.update({
          where: { id: user.id },
          data: { failedLoginAttempts: 0, lockedUntil: new Date(Date.now() + 15 * 60 * 1000) },
        });
      } else {
        await prisma.user.update({
          where: { id: user.id },
          data: { failedLoginAttempts: next },
        });
      }
    }
    return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }

  const u = user!;

  await prisma.user.update({
    where: { id: u.id },
    data: { failedLoginAttempts: 0, lockedUntil: null },
  });

  if (u.totpEnabledAt) {
    return NextResponse.json({
      requireTotp: true,
      challenge: challengeToken(u.id, "TOTP", u.email, "totp-challenge"),
    });
  }

  const trusted = getTokenFromRequest(req, "trusted_device");
  if (trusted && verifyTrustedDevice(trusted, u.id, u.sessionEpoch)) {
    const accessToken = signToken({ userId: u.id, email: u.email, role: u.role });
    const refreshToken = generateRefreshToken();
    await prisma.refreshToken.create({
      data: {
        userId: u.id,
        tokenHash: hashRefreshToken(refreshToken),
        expiresAt: new Date(Date.now() + REFRESH_TOKEN_MAX_AGE_SECONDS * 1000),
      },
    });

    const res = NextResponse.json({
      user: { id: u.id, name: u.name, email: u.email, role: u.role },
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

  const channel = u.phoneVerifiedAt && u.phone ? "PHONE" : "EMAIL";
  const target = channel === "PHONE" ? u.phone! : u.email;

  // A code was already sent to this target and is still valid — present that
  // challenge instead of failing on the send cooldown. Codes are single-use
  // per login (OTP_CHALLENGE_EXPIRY + verify consumes), so reuse is safe.
  const active = await activeOtpCode(target, channel);
  if (active) {
    return NextResponse.json({
      requireOtp: true,
      challenge: challengeToken(u.id, channel, target),
      channel,
      targetMasked: maskFor(channel, target),
      expiresInSec: active.expiresInSec,
    });
  }

  const issued = await issueOtpCode(target, channel, u.id);
  if (!issued.ok) {
    return NextResponse.json({ error: issued.error }, { status: 429 });
  }

  return NextResponse.json({
    requireOtp: true,
    challenge: challengeToken(u.id, channel, target),
    channel,
    targetMasked: maskFor(channel, target),
    expiresInSec: issued.expiresInSec,
    debugCode: issued.debugCode,
  });
}