import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";
import { decryptSecret, verifyTotpCode } from "@/lib/totp";

const bodySchema = z.object({ code: z.string().trim().min(6).max(6) });

function requireUser(req: Request) {
  const token = getTokenFromRequest(req);
  return token ? verifyToken(token) : null;
}

export async function POST(req: Request) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const parsed = bodySchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }

  const dbUser = await prisma.user.findUnique({ where: { id: user.userId } });
  if (!dbUser?.totpEnabledAt || !dbUser.totpSecret) {
    return NextResponse.json({ error: "Authenticator is not enabled" }, { status: 400 });
  }

  let secret: string;
  try {
    secret = decryptSecret(dbUser.totpSecret);
  } catch {
    return NextResponse.json({ error: "Authenticator unavailable" }, { status: 500 });
  }

  if (!verifyTotpCode(parsed.data.code, secret, dbUser.id)) {
    return NextResponse.json({ error: "Incorrect code" }, { status: 401 });
  }

  await prisma.$transaction([
    prisma.user.update({
      where: { id: dbUser.id },
      data: { totpSecret: null, totpEnabledAt: null },
    }),
    prisma.recoveryCode.deleteMany({ where: { userId: dbUser.id } }),
  ]);

  return NextResponse.json({ ok: true });
}