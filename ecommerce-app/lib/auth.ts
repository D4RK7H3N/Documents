import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import crypto from "node:crypto";

const JWT_SECRET = process.env.JWT_SECRET ?? "";

if (!JWT_SECRET || JWT_SECRET === "change-this-to-a-long-random-string") {
  throw new Error(
    "[auth] JWT_SECRET is missing or still the template default — generate a strong random value (e.g. `node -e \"console.log(require('crypto').randomBytes(48).toString('base64url'))\"`) and set it in .env",
  );
}

export const ACCESS_TOKEN_MAX_AGE_SECONDS = 60 * 15; // 15 minutes
export const REFRESH_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 30; // 30 days

const JWT_ISSUER = "clickbound-commerce";
const JWT_AUDIENCE = "clickbound-commerce-users";

// Precomputed dummy hash used to equalize bcrypt cost when a user is not found,
// so login timing does not reveal whether an email address exists.
const DUMMY_PASSWORD_HASH = bcrypt.hashSync("dummy-password-for-timing", 12);

export interface TokenPayload {
  userId: string;
  email: string;
  role: "CUSTOMER" | "ADMIN";
}

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 12);
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

export async function verifyPasswordConstantTime(
  password: string,
  hash: string | null,
): Promise<boolean> {
  if (!hash) {
    await bcrypt.compare(password, DUMMY_PASSWORD_HASH);
    return false;
  }
  return bcrypt.compare(password, hash);
}

export function signToken(payload: TokenPayload): string {
  if (!JWT_SECRET) throw new Error("JWT_SECRET is not set");
  return jwt.sign(payload, JWT_SECRET, {
    expiresIn: "15m",
    issuer: JWT_ISSUER,
    audience: JWT_AUDIENCE,
  });
}

export function verifyToken(token: string): TokenPayload | null {
  try {
    if (!JWT_SECRET) throw new Error("JWT_SECRET is not set");
    return jwt.verify(token, JWT_SECRET, {
      issuer: JWT_ISSUER,
      audience: JWT_AUDIENCE,
    }) as TokenPayload;
  } catch {
    return null;
  }
}

export function generateRefreshToken(): string {
  return crypto.randomBytes(64).toString("hex");
}

export function hashRefreshToken(token: string): string {
  return crypto.createHash("sha256").update(token).digest("hex");
}

export function getTokenFromRequest(req: Request, cookieName = "token"): string | null {
  const authHeader = req.headers.get("authorization");
  if (authHeader?.startsWith("Bearer ")) return authHeader.slice(7);

  const cookieHeader = req.headers.get("cookie");
  if (!cookieHeader) return null;
  const match = cookieHeader.match(new RegExp(`${cookieName}=([^;]+)`));
  return match ? match[1] : null;
}
