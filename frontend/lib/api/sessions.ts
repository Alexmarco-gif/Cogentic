/**
 * User sessions API service.
 *
 * Maps to: backend/api/v1/users.py  (GET/DELETE /users/me/sessions)
 *
 * Sessions are self-hosted — no Auth0 Sessions Management add-on needed.
 */

import { get, del } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────────

export interface SessionApiItem {
  id: string;
  device: string;
  ip_address: string;
  last_active_at: string; // ISO 8601
  created_at: string;     // ISO 8601
  is_current: boolean;
}

/** Alias kept for component imports. */
export type UserSession = SessionApiItem;

// ── Helpers ───────────────────────────────────────────────────────────────────────

/** Format an ISO timestamp into a human-friendly "last seen" string. */
export function formatLastSeen(isoString: string, isCurrent: boolean): string {
  if (isCurrent) return 'Active now';
  const delta = Date.now() - new Date(isoString).getTime();
  const secs  = Math.floor(delta / 1000);
  if (secs < 120)    return 'Just now';
  if (secs < 3600)   return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400)  return `${Math.floor(secs / 3600)}h ago`;
  if (secs < 172800) return 'Yesterday';
  return new Date(isoString).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
  });
}

// ── API calls ─────────────────────────────────────────────────────────────────────────

/** GET /api/v1/users/me/sessions */
export function listMySessions(): Promise<SessionApiItem[]> {
  return get<SessionApiItem[]>('/users/me/sessions');
}

/** DELETE /api/v1/users/me/sessions/:id */
export function revokeMySession(sessionId: string): Promise<void> {
  return del<void>(`/users/me/sessions/${sessionId}`);
}

/** DELETE /api/v1/users/me/sessions — revoke all except current */
export function revokeAllOtherSessions(): Promise<void> {
  return del<void>('/users/me/sessions');
}
