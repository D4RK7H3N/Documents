// ============================================================================
// auth.js — JWT Authentication & Password Hashing
// Cloudflare Workers runtime: uses Web Crypto API (NOT Node.js crypto)
// No 'bcrypt' — PBKDF2 via Web Crypto SubtleCrypto instead
// ============================================================================

import { SignJWT, jwtVerify } from 'jose';

// ============================================================================
// PASSWORD HASHING (PBKDF2-SHA256)
// ============================================================================

/**
 * Generate a PBKDF2 hash.
 * Returns format: salt_hex:hash_hex
 * Salt: 16 random bytes
 * Iterations: 100000 (OWASP recommended minimum)
 */
export async function hashPassword(password) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(password),
    'PBKDF2',
    false,
    ['deriveBits']
  );
  const hashBuffer = await crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      salt,
      iterations: 100000,
      hash: 'SHA-256',
    },
    keyMaterial,
    256 // 32 bytes output
  );
  const saltHex = Array.from(salt).map(b => b.toString(16).padStart(2, '0')).join('');
  const hashHex = Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('');
  return `${saltHex}:${hashHex}`;
}

/**
 * Verify a password against a stored hash.
 */
export async function verifyPassword(password, storedHash) {
  const [saltHex, hashHex] = storedHash.split(':');
  if (!saltHex || !hashHex) return false;
  const salt = new Uint8Array(saltHex.match(/.{1,2}/g).map(b => parseInt(b, 16)));
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(password),
    'PBKDF2',
    false,
    ['deriveBits']
  );
  const hashBuffer = await crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      salt,
      iterations: 100000,
      hash: 'SHA-256',
    },
    keyMaterial,
    256
  );
  const computedHash = Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('');
  return computedHash === hashHex;
}

// ============================================================================
// JWT TOKENS (using jose library)
// ============================================================================

/**
 * Create a JWT secret key from the env variable.
 */
function getSecretKey(secret) {
  return new TextEncoder().encode(secret);
}

/**
 * Generate a JWT token.
 * Payload: { sub: userId, role, name }
 */
export async function createToken(user, secret, expiry = '8h') {
  const jwt = await new SignJWT({
    sub: String(user.id),
    role: user.role,
    name: user.full_name,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(expiry)
    .sign(getSecretKey(secret));
  return jwt;
}

/**
 * Verify and decode a JWT token.
 * Returns { payload, protectedHeader } or throws.
 */
export async function verifyToken(token, secret) {
  const { payload, protectedHeader } = await jwtVerify(
    token,
    getSecretKey(secret)
  );
  return { payload, protectedHeader };
}
