/**
 * Privacy & data management API service.
 *
 * Covers:
 *  - Clear all user history (bulk delete chat sessions)
 *  - Request account data deletion (GDPR)
 *  - Request full data archive export
 */

import { del, get, post } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ClearHistoryResponse {
  deleted_sessions: number;
  message: string;
}

export interface DeletionRequestResponse {
  request_id: string;
  status: string;
  message: string;
}

export interface DataExportRequestResponse {
  request_id: string;
  status: string;
  message: string;
  data: Record<string, unknown> | null;
}

export type ConsentType = 'data_processing' | 'marketing' | 'analytics' | 'ai_training';

export interface ConsentResponse {
  user_id: string;
  consent_type: ConsentType;
  granted: boolean;
  recorded_at: string;
}

export interface ConsentHistoryEntry {
  action: string;
  consent_type: ConsentType | null;
  granted: boolean | null;
  ip_address: string | null;
  recorded_at: string | null;
}

// ── Service functions ─────────────────────────────────────────────────────────

/**
 * Permanently deletes all chat sessions + messages for the current user.
 * Returns the number of sessions deleted.
 */
export async function clearUserHistory(): Promise<ClearHistoryResponse> {
  return del<ClearHistoryResponse>('/users/me/history');
}

/**
 * Executes a GDPR-compliant account data deletion request.
 * The backend deletes user data immediately and returns a completion summary.
 */
export async function requestDataDeletion(): Promise<DeletionRequestResponse> {
  return post<DeletionRequestResponse>('/users/me/deletion-request');
}

/**
 * Requests a full portable data archive (contracts, briefs, sessions).
 * The backend returns the export payload immediately and also emails a confirmation.
 */
export async function requestDataExport(): Promise<DataExportRequestResponse> {
  return post<DataExportRequestResponse>('/users/me/data-export-request');
}

export async function updateConsentDecision(
  consent_type: ConsentType,
  granted: boolean,
): Promise<ConsentResponse> {
  return post<ConsentResponse>('/users/me/consent', { consent_type, granted });
}

export async function getConsentHistory(): Promise<ConsentHistoryEntry[]> {
  return get<ConsentHistoryEntry[]>('/users/me/consent/history');
}
