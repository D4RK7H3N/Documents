import { NextResponse } from "next/server";
import QRCode from "qrcode";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";
import { encryptSecret, generateTotpSecret, totpUri } from "@/lib/totp";

function requireUser(req: Request) {
  const token = getTokenFromRequest(req);
  return token ? verifyToken(token) : null;
}

export async function GET(req: Request) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const dbUser = await prisma.user.findUnique({ where: { id: user.userId } });
  if (dbUser?.totpEnabledAt) {
    return NextResponse.json({ error: "Authenticator is already enabled" }, { status: 409 });
  }

  const secret = generateTotpSecret();
  await prisma.user.update({
    where: { id: user.userId },
    data: { totpSecret: encryptSecret(secret) },
  });

  const uri = totpUri(secret, user.email);
  const qr = await QRCode.toDataURL(uri);

  return NextResponse.json({ secret, uri, qr });
}