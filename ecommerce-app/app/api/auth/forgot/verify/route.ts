import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { hashPassword } from "@/lib/auth";
import { verifyOtpCode } from "@/lib/otp";
import { checkRateLimit, rateLimitKey } from "@/lib/rate-limit";

const bodySchema = z.object({
  email: z.string().email(),
  code: z.string().trim().min(6).max(6),
  newPassword: z.string().min(8).optional(),
});

export async function POST(req: Request) {
  const rate = checkRateLimit(`forgot-verify:${rateLimitKey(req)}`, 10, 15 * 60 * 1000);
  if (!rate.allowed) {
    return NextResponse.json(
      { error: "Too many attempts. Try again later." },
      { status: 429, headers: { "Retry-After": String(Math.ceil((rate.retryAfterMs ?? 0) / 1000)) } },
    );
  }

  const body = await req.json().catch(() => ({}));
  const parsed = bodySchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }

  const email = parsed.data.email.toLowerCase();

  const result = await verifyOtpCode(email, "EMAIL", parsed.data.code, !!parsed.data.newPassword);
  if (!result.ok) {
    return NextResponse.json(
      { error: result.error, attemptsLeft: result.attemptsLeft },
      { status: 401 },
    );
  }

  const user = await prisma.user.findUnique({ where: { email } });
  if (!user) {
    return NextResponse.json({ error: "Account not found" }, { status: 404 });
  }

  // Step 1: verify the code only (not consumed yet) so the UI can move to the
  // new-password step. The full reset below re-verifies and consumes it.
  if (!parsed.data.newPassword) {
    return NextResponse.json({ ok: true, verified: true });
  }

  const hashed = await hashPassword(parsed.data.newPassword);

  await prisma.$transaction([
    // New password + kill every session: bump the epoch (invalidates all
    // trusted-device cookies) and revoke all refresh tokens.
    prisma.user.update({
      where: { id: user.id },
      data: { password: hashed, sessionEpoch: { increment: 1 } },
    }),
    prisma.refreshToken.updateMany({
      where: { userId: user.id, revokedAt: null },
      data: { revokedAt: new Date() },
    }),
    prisma.otpCode.deleteMany({ where: { target: email, channel: "EMAIL" } }),
  ]);

  return NextResponse.json({ ok: true });
}