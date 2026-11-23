import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import {
  ACCESS_TOKEN_MAX_AGE_SECONDS,
  REFRESH_TOKEN_MAX_AGE_SECONDS,
  generateRefreshToken,
  hashRefreshToken,
  signToken,
} from "@/lib/auth";
import { trustedDeviceToken, verifyChallenge, verifyOtpCode } from "@/lib/otp";
import {
  decryptSecret,
  isRecoveryCodeFormat,
  verifyRecoveryCode,
  verifyTotpCode,
} from "@/lib/totp";

const bodySchema = z.object({
  challenge: z.string(),
  code: z.string().trim(),
  remember: z.boolean().optional(),
});

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const parsed = bodySchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }

  const challenge = verifyChallenge(parsed.data.challenge);
  if (!challenge) {
    return NextResponse.json({ error: "Login session expired. Try again." }, { status: 400 });
  }

  const user = await prisma.user.findUnique({ where: { id: challenge.userId } });
  if (!user) {
    return NextResponse.json({ error: "User not found" }, { status: 404 });
  }

  const code = parsed.data.code;

  if (challenge.kind === "totp-challenge") {
    if (!/^\d{6}$/.test(code)) {
      if (!isRecoveryCodeFormat(code)) {
        return NextResponse.json(
          { error: "Enter a 6-digit authenticator code or a recovery code" },
          { status: 400 },
        );
      }
      const candidates = await prisma.recoveryCode.findMany({
        where: { userId: user.id, usedAt: null },
      });
      let matched = false;
      for (const row of candidates) {
        if (await verifyRecoveryCode(code, row.codeHash)) {
          await prisma.recoveryCode.update({
            where: { id: row.id },
            data: { usedAt: new Date() },
          });
          matched = true;
          break;
        }
      }
      if (!matched) {
        return NextResponse.json({ error: "Invalid recovery code" }, { status: 401 });
      }
    } else {
      if (!user.totpSecret) {
        return NextResponse.json(
          { error: "Authenticator is not set up for this account" },
          { status: 401 },
        );
      }
      let secret: string;
      try {
        secret = decryptSecret(user.totpSecret);
      } catch {
        return NextResponse.json({ error: "Authenticator unavailable" }, { status: 500 });
      }
      if (!verifyTotpCode(code, secret, user.id)) {
        return NextResponse.json({ error: "Incorrect code" }, { status: 401 });
      }
    }
  } else {
    if (!/^\d{6}$/.test(code)) {
      return NextResponse.json({ error: "Code must be 6 digits" }, { status: 400 });
    }
    const result = await verifyOtpCode(challenge.target, challenge.channel, code);
    if (!result.ok) {
      return NextResponse.json(
        { error: result.error, attemptsLeft: result.attemptsLeft },
        { status: 401 },
      );
    }
  }

  await prisma.user.update({
    where: { id: user.id },
    data: { failedLoginAttempts: 0, lockedUntil: null },
  });

  if (challenge.kind === "login-challenge" && challenge.channel === "EMAIL" && !user.emailVerifiedAt) {
    await prisma.user.update({
      where: { id: user.id },
      data: { emailVerifiedAt: new Date() },
    });
  }

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

  if (parsed.data.remember) {
    res.cookies.set("trusted_device", trustedDeviceToken(user.id, user.sessionEpoch), {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 30,
      path: "/",
    });
  }

  return res;
}