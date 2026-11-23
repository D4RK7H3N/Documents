import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { notifyAdmins } from "@/lib/notify";

export const dynamic = "force-dynamic";

const contactSchema = z.object({
  name: z.string().min(1).max(80),
  email: z.string().email(),
  message: z.string().min(10).max(2000),
});

export async function POST(req: Request) {
  const body = await req.json();
  const parsed = contactSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json({ error: parsed.error.flatten() }, { status: 400 });
  }

  const { name, email, message } = parsed.data;

  await prisma.contactMessage.create({
    data: { name, email, message },
  });

  await notifyAdmins(
    "CONTACT_MESSAGE",
    `${name} (${email}) sent a message: ${message.slice(0, 120)}${message.length > 120 ? "…" : ""}`,
  );

  return Response.json({ ok: true }, { status: 201 });
}
