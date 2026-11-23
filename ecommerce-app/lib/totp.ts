import crypto from "node:crypto";
import bcrypt from "bcryptjs";

const JWT_SECRET = process.env.JWT_SECRET ?? "";

const BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
const TOTP_PERIOD_SECONDS = 30;
const TOTP_DIGITS = 6;
const TOTP_WINDOW = 1; // allow ±1 step

// RFC 4648 base32 encoding (no padding)
function base32Encode(input: Buffer): string {
  let bits = 0;
  let value = 0;
  let out = "";
  for (const byte of input) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      out += BASE32_ALPHABET[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) out += BASE32_ALPHABET[(value << (5 - bits)) & 31];
  return out;
}

function base32Decode(input: string): Buffer {
  const clean = input.toUpperCase().replace(/[^A-Z2-7]/g, "");
  let bits = 0;
  let value = 0;
  const bytes: number[] = [];
  for (const ch of clean) {
    value = (value << 5) | BASE32_ALPHABET.indexOf(ch);
    bits += 5;
    if (bits >= 8) {
      bytes.push((value >>> (bits - 8)) & 255);
      bits -= 8;
    }
  }
  return Buffer.from(bytes);
}

function totpCounter(now = Date.now()): number {
  return Math.floor(now / 1000 / TOTP_PERIOD_SECONDS);
}

function hotp(secret: Buffer, counter: number): string {
  const counterBuf = Buffer.alloc(8);
  counterBuf.writeBigUInt64BE(BigInt(counter));
  const hmac = crypto.createHmac("sha1", secret).update(counterBuf).digest();
  const offset = hmac[hmac.length - 1] & 0x0f;
  const code =
    ((hmac[offset] & 0x7f) << 24) |
    ((hmac[offset + 1] & 0xff) << 16) |
    ((hmac[offset + 2] & 0xff) << 8) |
    (hmac[offset + 3] & 0xff);
  return String(code % 10 ** TOTP_DIGITS).padStart(TOTP_DIGITS, "0");
}

// Replay guard: userId -> last accepted TOTP counter. In-memory only — see the
// same caveat as the rate limiter (fine for a single dev/staging instance).
const lastUsedCounter = new Map<string, number>();

export function generateTotpSecret(): string {
  return base32Encode(crypto.randomBytes(20));
}

export function totpUri(secret: string, email: string): string {
  const params = new URLSearchParams({
    secret,
    issuer: "Clickbound",
    algorithm: "SHA1",
    digits: String(TOTP_DIGITS),
    period: String(TOTP_PERIOD_SECONDS),
  });
  return `otpauth://totp/Clickbound:${encodeURIComponent(email)}?${params.toString()}`;
}

export function verifyTotpCode(code: string, secret: string, userId?: string): boolean {
  if (!/^\d{6}$/.test(code)) return false;
  const key = base32Decode(secret);
  const step = totpCounter();
  for (const offset of [-TOTP_WINDOW, 0, TOTP_WINDOW]) {
    const candidate = hotp(key, step + offset);
    const expected = Buffer.from(candidate);
    const actual = Buffer.from(code);
    if (expected.length === actual.length && crypto.timingSafeEqual(expected, actual)) {
      if (userId) {
        const prev = lastUsedCounter.get(userId);
        if (prev !== undefined && prev >= step + offset) return false; // replay
        lastUsedCounter.set(userId, step + offset);
      }
      return true;
    }
  }
  return false;
}

function encryptionKey(): Buffer {
  return crypto.createHash("sha256").update(JWT_SECRET).digest();
}

export function encryptSecret(secret: string): string {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", encryptionKey(), iv);
  const encrypted = Buffer.concat([cipher.update(secret, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return [iv.toString("base64"), tag.toString("base64"), encrypted.toString("base64")].join(":");
}

export function decryptSecret(payload: string): string {
  const [ivB64, tagB64, dataB64] = payload.split(":");
  const decipher = crypto.createDecipheriv("aes-256-gcm", encryptionKey(), Buffer.from(ivB64, "base64"));
  decipher.setAuthTag(Buffer.from(tagB64, "base64"));
  return Buffer.concat([decipher.update(Buffer.from(dataB64, "base64")), decipher.final()]).toString("utf8");
}

const RECOVERY_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"; // no ambiguous chars

export function generateRecoveryCodes(count = 10): string[] {
  const codes: string[] = [];
  for (let i = 0; i < count; i++) {
    const bytes = crypto.randomBytes(8);
    let raw = "";
    for (const b of bytes) raw += RECOVERY_CHARS[b % RECOVERY_CHARS.length];
    codes.push(`${raw.slice(0, 4)}-${raw.slice(4, 8)}`);
  }
  return codes;
}

export async function hashRecoveryCode(code: string): Promise<string> {
  return bcrypt.hash(code.toUpperCase().replace("-", ""), 10);
}

export async function verifyRecoveryCode(code: string, hash: string): Promise<boolean> {
  return bcrypt.compare(code.toUpperCase().replace("-", ""), hash);
}

export function isRecoveryCodeFormat(code: string): boolean {
  return /^[A-Za-z0-9]{4}-[A-Za-z0-9]{4}$/.test(code.trim());
}
