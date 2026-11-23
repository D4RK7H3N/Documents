import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { verifyNewsletterUnsubscribeToken } from "@/lib/otp";

const bodySchema = z.object({
  token: z.string().min(1),
});

function unsubscribeWithToken(token: string) {
  const claims = verifyNewsletterUnsubscribeToken(token);
  if (!claims) return null;
  return prisma.newsletterSubscriber.deleteMany({ where: { email: claims.email } });
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const parsed = bodySchema.safeParse(body);
  if (!parsed.success) {
    return Response.json({ error: "Invalid input" }, { status: 400 });
  }

  const result = await unsubscribeWithToken(parsed.data.token);
  if (!result || result.count === 0) {
    return Response.json({ error: "Invalid or expired unsubscribe link" }, { status: 400 });
  }

  return Response.json({ ok: true });
}

export async function GET(req: Request) {
  const token = new URL(req.url).searchParams.get("token") ?? "";
  const result = await unsubscribeWithToken(token);
  if (!result || result.count === 0) {
    return new Response(
      "<!DOCTYPE html><html><body style=\"font-family:system-ui;padding:2rem\"><h1>Unsubscribe link invalid or expired</h1><p>You can close this page.</p></body></html>",
      { status: 400, headers: { "Content-Type": "text/html; charset=utf-8" } },
    );
  }

  return new Response(
    "<!DOCTYPE html><html><body style=\"font-family:system-ui;padding:2rem\"><h1>You've been unsubscribed</h1><p>You will no longer receive Clickbound newsletter emails. You can close this page.</p></body></html>",
    { status: 200, headers: { "Content-Type": "text/html; charset=utf-8" } },
  );
}
