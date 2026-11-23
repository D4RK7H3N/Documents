import { prisma } from "@/lib/prisma";

export function notifyUser(
  userId: string,
  type: string,
  message: string,
  link?: string,
) {
  return prisma.notification.create({
    data: { userId, type, message, link },
  });
}

export async function notifyAdmins(
  type: string,
  message: string,
  link?: string,
) {
  const admins = await prisma.user.findMany({
    where: { role: "ADMIN" },
    select: { id: true },
  });
  if (admins.length === 0) return;
  await prisma.notification.createMany({
    data: admins.map((a) => ({ userId: a.id, type, message, link })),
  });
}