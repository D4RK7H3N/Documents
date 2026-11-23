import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken, hashPassword, verifyPassword, signToken, ACCESS_TOKEN_MAX_AGE_SECONDS } from "@/lib/auth";
import { verifyProof } from "@/lib/otp";

function requireUser(req: Request) {
  const token = getTokenFromRequest(req);
  return token ? verifyToken(token) : null;
}

export async function GET(req: Request) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const dbUser = await prisma.user.findUnique({
    where: { id: user.userId },
    select: {
      id: true,
      name: true,
      email: true,
      role: true,
      addressLine: true,
      city: true,
      zipCode: true,
      phone: true,
      totpEnabledAt: true,
      createdAt: true,
    },
  });
  if (!dbUser) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  return NextResponse.json({ user: dbUser });
}

const updateSchema = z.object({
  name: z.string().trim().min(2).optional(),
  email: z.string().email().optional(),
  emailProof: z.string().min(1).optional(),
  currentPassword: z.string().min(1).optional(),
  newPassword: z.string().min(8).optional(),
  addressLine: z.string().trim().max(200).optional().nullable(),
  city: z.string().trim().max(100).optional().nullable(),
  zipCode: z.string().trim().max(20).optional().nullable(),
  phone: z.string().trim().min(7).max(20).optional().nullable(),
});

export async function PATCH(req: Request) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();
  const parsed = updateSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const { name, email, emailProof, currentPassword, newPassword, addressLine, city, zipCode, phone } =
    parsed.data;

  if (!!currentPassword !== !!newPassword) {
    return NextResponse.json(
      { error: "Both current and new password are required" },
      { status: 400 }
    );
  }

  const dbUser = await prisma.user.findUnique({ where: { id: user.userId } });
  if (!dbUser) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const data: {
    name?: string;
    email?: string;
    password?: string;
    addressLine?: string | null;
    city?: string | null;
    zipCode?: string | null;
    phone?: string | null;
  } = {};
  if (name) data.name = name;
  if (email && email !== dbUser.email) {
    const emailLower = email.toLowerCase();
    const proof = verifyProof(emailProof ?? "", "email-proof");
    if (!proof || proof.email !== emailLower) {
      return NextResponse.json(
        { error: "Verify your new email first to change it" },
        { status: 400 }
      );
    }
    const taken = await prisma.user.findUnique({ where: { email: emailLower } });
    if (taken) {
      return NextResponse.json({ error: "Email already registered" }, { status: 409 });
    }
    data.email = emailLower;
  }
  if (addressLine !== undefined) data.addressLine = addressLine || null;
  if (city !== undefined) data.city = city || null;
  if (zipCode !== undefined) data.zipCode = zipCode || null;
  if (phone !== undefined) data.phone = phone || null;

  if (currentPassword && newPassword) {
    const valid = await verifyPassword(currentPassword, dbUser.password);
    if (!valid) {
      return NextResponse.json({ error: "Current password is incorrect" }, { status: 401 });
    }
    data.password = await hashPassword(newPassword);
  }

  const updated = await prisma.user.update({ where: { id: user.userId }, data });

  const res = NextResponse.json({
    user: {
      id: updated.id,
      name: updated.name,
      email: updated.email,
      role: updated.role,
      createdAt: updated.createdAt,
    },
  });

  if (data.email) {
    res.cookies.set(
      "token",
      signToken({ userId: updated.id, email: updated.email, role: updated.role }),
      {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS,
        path: "/",
      }
    );
  }

  return res;
}
