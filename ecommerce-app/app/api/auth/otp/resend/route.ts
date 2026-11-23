import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import {
  challengeToken,
  issueOtpCode,
  maskFor,
  verifyChallenge,
} from "@/lib/otp";
import type { OtpChannelName } from "@/lib/channels";

const bodySchema = z.object({
  challenge: z.string(),
  emailInstead: z.boolean().optional(),
});

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const parsed = bodySchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }

  const challenge = verifyChallenge(parsed.data.challenge);
  if (!challenge) {
    return NextResponse.json({ error: "Login session expired. Log in again." }, { status: 400 });
  }

  const user = await prisma.user.findUnique({ where: { id: challenge.userId } });
  if (!user) {
    return NextResponse.json({ error: "User not found" }, { status: 404 });
  }

  if (challenge.kind !== "login-challenge") {
    return NextResponse.json({ error: "This challenge can't be resent" }, { status: 400 });
  }

  let channel: OtpChannelName = challenge.channel;
  let target = challenge.target;

  if (parsed.data.emailInstead && channel === "PHONE" && user.email) {
    channel = "EMAIL";
    target = user.email;
  }

  const issued = await issueOtpCode(target, channel, user.id);
  if (!issued.ok) {
    return NextResponse.json({ error: issued.error }, { status: 429 });
  }

  return NextResponse.json({
    challenge: challengeToken(user.id, channel, target),
    channel,
    targetMasked: maskFor(channel, target),
    expiresInSec: issued.expiresInSec,
    debugCode: issued.debugCode,
  });
}