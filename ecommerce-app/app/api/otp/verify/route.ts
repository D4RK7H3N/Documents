import { NextResponse } from "next/server";
import { z } from "zod";
import { emailProofToken, phoneProofToken, verifyOtpCode } from "@/lib/otp";

const bodySchema = z.object({
  channel: z.enum(["EMAIL", "PHONE"]),
  target: z.string().trim(),
  code: z.string().trim(),
});

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const parsed = bodySchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }

  const { channel, target, code } = parsed.data;
  if (!/^\d{6}$/.test(code)) {
    return NextResponse.json({ error: "Code must be 6 digits" }, { status: 400 });
  }

  const result = await verifyOtpCode(target, channel, code);
  if (!result.ok) {
    return NextResponse.json(
      { error: result.error, attemptsLeft: result.attemptsLeft },
      { status: 401 },
    );
  }

  const proof =
    channel === "EMAIL" ? emailProofToken(target) : phoneProofToken(target);

  return NextResponse.json({ ok: true, proof });
}