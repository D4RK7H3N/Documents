import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import { prisma } from "@/lib/prisma";
import { deliverOtpCode, isMockDelivery, maskTarget, type OtpChannelName } from "@/lib/channels";

const JWT_SECRET = process.env.JWT_SECRET as string;

export const OTP_TTL_MS = 10 * 60 * 1000;
export const OTP_MAX_ATTEMPTS = 5;
export const OTP_RESEND_COOLDOWN_MS = 60 * 1000;
export const OTP_HOURLY_LIMIT = 6;

const sendHistory = new Map<string, number[]>();

function rateKey(target: string, channel: OtpChannelName) {
  return `${channel}:${target.toLowerCase()}`;
}

export function isDev(): boolean {
  return process.env.NODE_ENV !== "production";
}

export function maskFor(channel: OtpChannelName, target: string): string {
  return maskTarget(channel, target);
}

function checkRateLimit(target: string, channel: OtpChannelName): { ok: boolean; error?: string } {
  const key = rateKey(target, channel);
  const now = Date.now();
  const hits = (sendHistory.get(key) ?? []).filter((t) => now - t < 60 * 60 * 1000);
  if (hits.length >= OTP_HOURLY_LIMIT) {
    return { ok: false, error: "Too many codes sent to this address. Try again later." };
  }
  const last = hits.at(-1);
  if (last && now - last < OTP_RESEND_COOLDOWN_MS) {
    const wait = Math.ceil((OTP_RESEND_COOLDOWN_MS - (now - last)) / 1000);
    return { ok: false, error: `Please wait ${wait}s before resending.` };
  }
  return { ok: true };
}

function recordSend(target: string, channel: OtpChannelName) {
  const key = rateKey(target, channel);
  const now = Date.now();
  const hits = (sendHistory.get(key) ?? []).filter((t) => now - t < 60 * 60 * 1000);
  hits.push(now);
  sendHistory.set(key, hits);
}

/**
 * Returns the still-usable code record for a target/channel, or null. Used by
 * login: if a code was already sent and is still valid, we present the existing
 * challenge instead of blocking on the send cooldown.
 */
export async function activeOtpCode(
  target: string,
  channel: OtpChannelName,
): Promise<{ expiresInSec: number } | null> {
  const record = await prisma.otpCode.findFirst({
    where: { target: target.toLowerCase(), channel },
    orderBy: { createdAt: "desc" },
  });
  if (!record) return null;
  if (record.expiresAt.getTime() <= Date.now()) return null;
  if (record.attempts >= OTP_MAX_ATTEMPTS) return null;
  return { expiresInSec: Math.floor((record.expiresAt.getTime() - Date.now()) / 1000) };
}

export async function issueOtpCode(target: string, channel: OtpChannelName, userId?: string) {
  const limit = checkRateLimit(target, channel);
  if (!limit.ok) return { ok: false as const, error: limit.error };

  const code = String(Math.floor(100000 + Math.random() * 900000));
  const codeHash = await bcrypt.hash(code, 10);

  await prisma.$transaction([
    prisma.otpCode.deleteMany({ where: { target: target.toLowerCase(), channel } }),
    prisma.otpCode.create({
      data: {
        target: target.toLowerCase(),
        channel,
        codeHash,
        expiresAt: new Date(Date.now() + OTP_TTL_MS),
        userId,
      },
    }),
  ]);
  recordSend(target, channel);

  try {
    await deliverOtpCode({ channel, target, code });
  } catch (err) {
    console.error(`[otp-send-failed] ${channel} -> ${target}:`, err);
    return { ok: false as const, error: "Couldn't send the code — please try again." };
  }

  return {
    ok: true as const,
    expiresInSec: Math.floor(OTP_TTL_MS / 1000),
    debugCode: isDev() && isMockDelivery(channel, target) ? code : undefined,
  };
}

export async function verifyOtpCode(
  target: string,
  channel: OtpChannelName,
  code: string,
  consume = true,
): Promise<{ ok: boolean; error?: string; attemptsLeft?: number }> {
  const record = await prisma.otpCode.findFirst({
    where: { target: target.toLowerCase(), channel },
    orderBy: { createdAt: "desc" },
  });

  if (!record) return { ok: false, error: "No code found for this address." };
  if (record.attempts >= OTP_MAX_ATTEMPTS) {
    await prisma.otpCode.delete({ where: { id: record.id } });
    return { ok: false, error: "Too many attempts. Request a new code." };
  }
  if (record.expiresAt < new Date()) {
    await prisma.otpCode.delete({ where: { id: record.id } });
    return { ok: false, error: "Code expired. Request a new one." };
  }

  const valid = await bcrypt.compare(code, record.codeHash);
  if (!valid) {
    const attemptsLeft = OTP_MAX_ATTEMPTS - (record.attempts + 1);
    await prisma.otpCode.update({
      where: { id: record.id },
      data: { attempts: { increment: 1 } },
    });
    if (attemptsLeft <= 0) {
      await prisma.otpCode.delete({ where: { id: record.id } });
      return { ok: false, error: "Too many attempts. Request a new code." };
    }
    return { ok: false, error: "Incorrect code.", attemptsLeft };
  }

  if (consume) await prisma.otpCode.delete({ where: { id: record.id } });
  return { ok: true, attemptsLeft: 0 };
}

function signProof(kind: string, claims: Record<string, string>) {
  return jwt.sign({ kind, ...claims }, JWT_SECRET, { expiresIn: "15m" });
}

export function verifyProof(token: string, kind: string): Record<string, string> | null {
  try {
    const payload = jwt.verify(token, JWT_SECRET) as Record<string, string> & { kind?: string };
    return payload.kind === kind ? payload : null;
  } catch {
    return null;
  }
}

export function emailProofToken(email: string) {
  return signProof("email-proof", { email: email.toLowerCase() });
}

export function phoneProofToken(phone: string) {
  return signProof("phone-proof", { phone });
}

export function newsletterUnsubscribeToken(email: string) {
  return signProof("newsletter-unsub", { email: email.toLowerCase() });
}

export function verifyNewsletterUnsubscribeToken(token: string): { email: string } | null {
  const payload = verifyProof(token, "newsletter-unsub");
  if (!payload || !payload.email) return null;
  return { email: payload.email };
}

export function challengeToken(
  userId: string,
  channel: OtpChannelName | "TOTP",
  target: string,
  kind: "login-challenge" | "totp-challenge" = "login-challenge",
) {
  return jwt.sign(
    { kind, userId, channel, target: target.toLowerCase() },
    JWT_SECRET,
    { expiresIn: "5m" },
  );
}

export type OTPChallenge =
  | { kind: "totp-challenge"; userId: string; channel: "TOTP"; target: string }
  | { kind: "login-challenge"; userId: string; channel: OtpChannelName; target: string };

export function verifyChallenge(token: string): OTPChallenge | null {
  try {
    const payload = jwt.verify(token, JWT_SECRET) as {
      kind?: "login-challenge" | "totp-challenge";
      userId: string;
      channel: OtpChannelName | "TOTP";
      target: string;
    };
    if (payload.kind !== "login-challenge" && payload.kind !== "totp-challenge") return null;
    return {
      kind: payload.kind,
      userId: payload.userId,
      channel: payload.channel,
      target: payload.target,
    } as OTPChallenge;
  } catch {
    return null;
  }
}

export function trustedDeviceToken(userId: string, epoch: number) {
  return jwt.sign({ kind: "trusted-device", userId, epoch }, JWT_SECRET, { expiresIn: "30d" });
}

export function verifyTrustedDevice(token: string, userId: string, expectedEpoch: number): boolean {
  try {
    const payload = jwt.verify(token, JWT_SECRET) as {
      kind?: string;
      userId?: string;
      epoch?: number;
    };
    return (
      payload.kind === "trusted-device" &&
      payload.userId === userId &&
      payload.epoch === expectedEpoch
    );
  } catch {
    return false;
  }
}