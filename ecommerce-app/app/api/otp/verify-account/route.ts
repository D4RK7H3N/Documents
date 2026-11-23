import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";
import { verifyOtpCode } from "@/lib/otp";

const PHONE_RE = /^[0-9+\-\s()]{8,20}$/;

const bodySchema = z.object({
  channel: z.enum(["EMAIL", "PHONE"]),
  code: z.string().trim(),
  phone: z.string().trim().optional(),
});

export async function POST(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  if (!payload) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const parsed = bodySchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }

  const user = await prisma.user.findUnique({ where: { id: payload.userId } });
  if (!user) return NextResponse.json({ error: "User not found" }, { status: 404 });

  const { channel, code } = parsed.data;

  if (channel === "EMAIL") {
    const result = await verifyOtpCode(user.email, channel, code);
    if (!result.ok) {
      return NextResponse.json({ error: result.error }, { status: 401 });
    }
    await prisma.user.update({
      where: { id: user.id },
      data: { emailVerifiedAt: new Date() },
    });
    return NextResponse.json({ ok: true, verified: "email" });
  }

  const newPhone = parsed.data.phone?.trim();
  if (newPhone && !PHONE_RE.test(newPhone)) {
    return NextResponse.json({ error: "Enter a valid phone number" }, { status: 400 });
  }
  const target = newPhone || user.phone;
  if (!target) {
    return NextResponse.json({ error: "No phone number on file" }, { status: 400 });
  }

  const result = await verifyOtpCode(target, "PHONE", code);
  if (!result.ok) {
    return NextResponse.json({ error: result.error }, { status: 401 });
  }

  const phoneTaken = newPhone
    ? await prisma.user.findFirst({ where: { phone: newPhone, id: { not: user.id } } })
    : null;
  if (phoneTaken) {
    return NextResponse.json({ error: "Phone already registered" }, { status: 409 });
  }

  await prisma.user.update({
    where: { id: user.id },
    data: { phone: newPhone ?? user.phone, phoneVerifiedAt: new Date() },
  });
  return NextResponse.json({ ok: true, verified: "phone" });
}