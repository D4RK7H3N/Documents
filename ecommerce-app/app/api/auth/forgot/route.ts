import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { isMockDelivery } from "@/lib/channels";
import { isDev, issueOtpCode } from "@/lib/otp";
import { checkRateLimit, rateLimitKey } from "@/lib/rate-limit";

const bodySchema = z.object({ email: z.string().email() });

export async function POST(req: Request) {
  const rate = checkRateLimit(`forgot:${rateLimitKey(req)}`, 5, 15 * 60 * 1000);
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
  const user = await prisma.user.findUnique({ where: { email } });

  let debugCode: string | undefined;
  if (user) {
    const issued = await issueOtpCode(email, "EMAIL", user.id);
    if (isDev() && isMockDelivery("EMAIL", email)) {
      debugCode = issued.ok ? issued.debugCode : undefined;
    }
  }

  // Identical response whether or not the account exists — no enumeration.
  return NextResponse.json({ ok: true, debugCode });
}