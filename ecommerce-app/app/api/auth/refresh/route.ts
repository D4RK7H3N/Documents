import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import {
  ACCESS_TOKEN_MAX_AGE_SECONDS,
  REFRESH_TOKEN_MAX_AGE_SECONDS,
  generateRefreshToken,
  getTokenFromRequest,
  hashRefreshToken,
  signToken,
} from "@/lib/auth";

function clearCookies() {
  const res = NextResponse.json({ error: "Invalid session" }, { status: 401 });
  res.cookies.set("token", "", { httpOnly: true, path: "/", maxAge: 0 });
  res.cookies.set("refreshToken", "", { httpOnly: true, path: "/api/auth", maxAge: 0 });
  return res;
}

export async function POST(req: Request) {
  const rawToken = getTokenFromRequest(req, "refreshToken");
  if (!rawToken) return clearCookies();

  const stored = await prisma.refreshToken.findUnique({
    where: { tokenHash: hashRefreshToken(rawToken) },
  });

  if (!stored || stored.expiresAt.getTime() <= Date.now()) {
    return clearCookies();
  }

  if (stored.revokedAt) {
    // A rotated token was used again — assume theft and revoke every session
    // for this account.
    await prisma.refreshToken.updateMany({
      where: { userId: stored.userId, revokedAt: null },
      data: { revokedAt: new Date() },
    });
    return clearCookies();
  }

  const user = await prisma.user.findUnique({ where: { id: stored.userId } });
  if (!user) return clearCookies();

  // Rotate: the presented token is revoked and a fresh one is issued, so a
  // stolen token can only be used once.
  const nextRefreshToken = generateRefreshToken();
  await prisma.$transaction([
    prisma.refreshToken.create({
      data: {
        userId: user.id,
        tokenHash: hashRefreshToken(nextRefreshToken),
        expiresAt: new Date(Date.now() + REFRESH_TOKEN_MAX_AGE_SECONDS * 1000),
      },
    }),
    prisma.refreshToken.update({
      where: { id: stored.id },
      data: { revokedAt: new Date() },
    }),
  ]);

  const accessToken = signToken({ userId: user.id, email: user.email, role: user.role });
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
  res.cookies.set("refreshToken", nextRefreshToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS,
    path: "/api/auth",
  });
  return res;
}
