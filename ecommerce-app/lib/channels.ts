import nodemailer from "nodemailer";
import type { Transporter } from "nodemailer";

export type OtpChannelName = "EMAIL" | "PHONE";

export interface OtpDelivery {
  channel: OtpChannelName;
  target: string;
  code: string;
}

export function maskTarget(channel: OtpChannelName, target: string): string {
  if (channel === "EMAIL") {
    const [name, domain] = target.split("@");
    const visible = name.slice(0, 2);
    return `${visible}●●●@${domain}`;
  }
  const digits = target.replace(/\D/g, "");
  const tail = digits.slice(-4);
  const head = digits.slice(0, 2);
  return head ? `${head} ●●● ${tail}` : `●●● ${tail}`;
}

// Addresses on these domains always use mock delivery, even when SMTP is
// configured — they are the seeded QA/dev accounts.
const DEV_DOMAINS = ["@clickbound.com"];

export function isEmailConfigured(): boolean {
  return Boolean(process.env.SMTP_HOST);
}

/**
 * True when a delivery should fall back to the dev/mock log instead of a
 * real channel — either because no provider is configured yet, or because the
 * target is one of the QA domains above.
 */
export function isMockDelivery(channel: OtpChannelName, target: string): boolean {
  if (channel === "EMAIL") {
    const lower = target.toLowerCase();
    return !isEmailConfigured() || DEV_DOMAINS.some((d) => lower.endsWith(d));
  }
  // PHONE: no SMS provider yet — always mock. A future Twilio/REST sender
  // slots in here without any caller changing.
  return true;
}

/**
 * Newsletter welcome email with an unsubscribe link. Same SMTP/mock seam as
 * OTP delivery: real mail when SMTP is configured and the address is not a
 * dev-domain, otherwise logged to the server console.
 */
export async function deliverNewsletterWelcome(info: {
  to: string;
  unsubscribeUrl: string;
}): Promise<void> {
  const to = info.to.toLowerCase();
  if (!isEmailConfigured() || DEV_DOMAINS.some((d) => to.endsWith(d))) {
    console.log(
      `[clickbound-newsletter] -> ${to}: welcome (mock) | unsubscribe: ${info.unsubscribeUrl}`,
    );
    return;
  }
  const from = process.env.SMTP_FROM ?? process.env.SMTP_USER ?? "no-reply@clickbound.local";
  await smtpTransport().sendMail({
    from,
    to,
    subject: "Welcome to Clickbound",
    text: `Thanks for joining Clickbound! If you didn't sign up, you can safely ignore this email.\n\nUnsubscribe: ${info.unsubscribeUrl}`,
    html: `<p>Thanks for joining Clickbound!</p><p style="color:#555">If you didn't sign up, you can safely ignore this email.</p><p><a href="${info.unsubscribeUrl}">Unsubscribe</a></p>`,
  });
}

let transporter: Transporter | null = null;

function smtpTransport(): Transporter {
  if (!transporter) {
    transporter = nodemailer.createTransport({
      host: process.env.SMTP_HOST,
      port: Number(process.env.SMTP_PORT ?? 587),
      secure: process.env.SMTP_SECURE === "true",
      auth: process.env.SMTP_USER
        ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS ?? "" }
        : undefined,
    });
  }
  return transporter;
}

async function sendEmail(info: OtpDelivery): Promise<void> {
  const from = process.env.SMTP_FROM ?? process.env.SMTP_USER ?? "no-reply@clickbound.local";
  const body = `Your Clickbound verification code is ${info.code}. It expires in 10 minutes. If you didn't request this, you can safely ignore this email.`;
  await smtpTransport().sendMail({
    from,
    to: info.target,
    subject: "Your Clickbound verification code",
    text: body,
    html: `<p>Your Clickbound verification code is</p>
<p style="font-size:28px;font-weight:700;letter-spacing:6px;margin:12px 0;">${info.code}</p>
<p style="color:#555">It expires in 10 minutes. If you didn't request this, you can safely ignore this email.</p>`,
  });
}

/**
 * Single delivery seam for OTP codes.
 * EMAIL: real SMTP when configured and the target is not a dev-domain; else
 *        mock (log to server console — the code also reaches the client via
 *        `debugCode` in dev replies).
 * PHONE: mock only for now (see isMockDelivery).
 * Throws on SMTP failure; callers are responsible for surfacing it.
 */
export async function deliverOtpCode(info: OtpDelivery): Promise<void> {
  if (info.channel === "EMAIL" && !isMockDelivery(info.channel, info.target)) {
    await sendEmail(info);
    return;
  }
  console.log(
    `[clickbound-otp:${info.channel}] -> ${info.target}: ${info.code} (expires 10 min) [mock]`,
  );
}