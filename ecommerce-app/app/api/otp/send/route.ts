import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { issueOtpCode } from "@/lib/otp";
import { checkRateLimit, rateLimitKey } from "@/lib/rate-limit";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^[0-9+\-\s()]{8,20}$/;

const bodySchema = z.object({
  channel: z.enum(["EMAIL", "PHONE"]),
  target: z.string().trim(),
  forSignup: z.boolean().optional(),
});

export async function POST(req: Request) {
  // Per-client cap on top of the per-target limits inside issueOtpCode, so an
  // attacker rotating targets cannot exhaust the server's CPU with bcrypt
  // hashing (each code costs a cost-10 hash).
  const rate = checkRateLimit(`otp-send:${rateLimitKey(req)}`, 10, 5 * 60 * 1000);
  if (!rate.allowed) {
    return NextResponse.json(
      { error: "Too many codes requested. Try again later." },
      { status: 429, headers: { "Retry-After": String(Math.ceil((rate.retryAfterMs ?? 0) / 1000)) } },
    );
  }

  const body = await req.json().catch(() => ({}));
  const parsed = bodySchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }

  const { channel, target, forSignup } = parsed.data;

  if (channel === "EMAIL" && !EMAIL_RE.test(target)) {
    return NextResponse.json({ error: "Enter a valid email address" }, { status: 400 });
  }
  if (channel === "PHONE" && !PHONE_RE.test(target)) {
    return NextResponse.json({ error: "Enter a valid phone number" }, { status: 400 });
  }

  if (forSignup) {
    if (channel === "EMAIL") {
      const existing = await prisma.user.findUnique({ where: { email: target.toLowerCase() } });
      if (existing) {
        return NextResponse.json({ error: "Email already registered" }, { status: 409 });
      }
    } else {
      const existing = await prisma.user.findFirst({ where: { phone: target } });
      if (existing) {
        return NextResponse.json({ error: "Phone already registered" }, { status: 409 });
      }
    }
  }

  const issued = await issueOtpCode(target, channel);
  if (!issued.ok) {
    return NextResponse.json({ error: issued.error }, { status: 429 });
  }

  return NextResponse.json({
    ok: true,
    expiresInSec: issued.expiresInSec,
    debugCode: issued.debugCode,
  });
}