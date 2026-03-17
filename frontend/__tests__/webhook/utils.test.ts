/**
 * Tests for frontend webhook utilities
 *
 * Covers:
 *  - verifyHmacSignature: correct sig, wrong sig, length mismatch (no crash)
 *  - verifyDirectToken: matching and non-matching tokens
 */

import { describe, it, expect } from 'vitest';
import crypto from 'crypto';
import { verifyHmacSignature, verifyDirectToken } from '@/lib/webhook-utils';

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeHmac(payload: string, secret: string): string {
  return crypto.createHmac('sha256', secret).update(payload).digest('hex');
}

// ── verifyHmacSignature ───────────────────────────────────────────────────────

describe('verifyHmacSignature', () => {
  it('returns true for a correct HMAC signature', () => {
    const secret = 'my-webhook-secret';
    const payload = JSON.stringify({ event: 'test', data: {} });
    const sig = makeHmac(payload, secret);
    expect(verifyHmacSignature(payload, sig, secret)).toBe(true);
  });

  it('returns false for a wrong signature', () => {
    const secret = 'my-webhook-secret';
    const payload = JSON.stringify({ event: 'test', data: {} });
    const wrongSig = makeHmac(payload, 'other-secret');
    expect(verifyHmacSignature(payload, wrongSig, secret)).toBe(false);
  });

  it('returns false when payload is tampered', () => {
    const secret = 'my-webhook-secret';
    const originalPayload = JSON.stringify({ event: 'test', data: {} });
    const tamperedPayload = JSON.stringify({ event: 'evil', data: {} });
    const sig = makeHmac(originalPayload, secret);
    expect(verifyHmacSignature(tamperedPayload, sig, secret)).toBe(false);
  });

  it('returns false (not crash) when signature length differs from expected', () => {
    // A static Bearer token (not a hex digest) must not throw
    const secret = 'my-webhook-secret';
    const payload = '{"event":"signup"}';
    const shortToken = 'short-token'; // different byte length than 64-char hex
    expect(() => verifyHmacSignature(payload, shortToken, secret)).not.toThrow();
    expect(verifyHmacSignature(payload, shortToken, secret)).toBe(false);
  });

  it('returns false for an empty signature', () => {
    const secret = 'my-webhook-secret';
    const payload = '{"event":"signup"}';
    expect(verifyHmacSignature(payload, '', secret)).toBe(false);
  });
});

// ── verifyDirectToken ─────────────────────────────────────────────────────────

describe('verifyDirectToken', () => {
  it('returns true when token matches secret exactly', () => {
    const secret = 'super-static-bearer-token-value';
    expect(verifyDirectToken(secret, secret)).toBe(true);
  });

  it('returns false when token does not match', () => {
    expect(verifyDirectToken('wrong-token', 'correct-secret')).toBe(false);
  });

  it('returns false when lengths differ', () => {
    expect(verifyDirectToken('short', 'much-longer-secret-value')).toBe(false);
  });

  it('returns false for empty token against non-empty secret', () => {
    expect(verifyDirectToken('', 'secret')).toBe(false);
  });

  it('does not throw for any input', () => {
    expect(() => verifyDirectToken('', '')).not.toThrow();
    expect(() => verifyDirectToken('a', 'b')).not.toThrow();
  });
});
