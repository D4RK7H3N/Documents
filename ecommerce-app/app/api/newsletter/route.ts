import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { newsletterUnsubscribeToken } from "@/lib/otp";
import { deliverNewsletterWelcome } from "@/lib/channels";
import { checkRateLimit, rateLimitKey } from "@/lib/rate-limit";

const newsletterSchema = z.object({
  email: z.string().email(),
});

export async function POST(req: Request) {
  const rate = checkRateLimit(`newsletter:${rateLimitKey(req)}`, 5, 15 * 60 * 1000);
  if (!rate.allowed) {
    return Response.json(
      { error: "Too many signups. Try again later." },
      {
        status: 429,
        headers: { "Retry-After": String(Math.ceil((rate.retryAfterMs ?? 0) / 1000)) },
      },
    );
  }

  const body = await req.json().catch(() => ({}));
  const parsed = newsletterSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json({ error: "Enter a valid email address" }, { status: 400 });
  }

  const email = parsed.data.email.toLowerCase();

  const existing = await prisma.newsletterSubscriber.findUnique({ where: { email } });
  if (existing) {
    return Response.json({ ok: true, already: true });
  }

  await prisma.newsletterSubscriber.create({ data: { email } });

  const origin = new URL(req.url).origin;
  const unsubscribeUrl = `${origin}/api/newsletter/unsubscribe?token=${newsletterUnsubscribeToken(email)}`;
  deliverNewsletterWelcome({ to: email, unsubscribeUrl }).catch((err) => {
    console.error(`[newsletter-send-failed] -> ${email}:`, err);
  });

  return Response.json({ ok: true }, { status: 201 });
}
