/**
 * Contracts API service.
 *
 * Maps to: backend/api/v1/contracts.py
 */

import { get, post, patch, del } from './client';
import type {
  SignalContractResponse,
  SignalContractListResponse,
  SignalContractCreate,
  SignalContractUpdate,
} from './types';

export interface ListContractsParams {
  skip?: number;
  limit?: number;
  industry_id?: string;
  source_type?: string;
  active_only?: boolean;
}

/** GET /api/v1/contracts */
export function listContracts(params?: ListContractsParams) {
  return get<SignalContractListResponse>('/contracts', { params: params as Record<string, string | number | boolean | undefined> });
}

/** GET /api/v1/contracts/degraded */
export function listDegradedContracts() {
  return get<SignalContractResponse[]>('/contracts/degraded');
}

/** GET /api/v1/contracts/:id */
export function getContract(contractId: string) {
  return get<SignalContractResponse>(`/contracts/${contractId}`);
}

/** POST /api/v1/contracts */
export function createContract(body: SignalContractCreate) {
  return post<SignalContractResponse>('/contracts', body);
}

/** PATCH /api/v1/contracts/:id */
export function updateContract(contractId: string, body: SignalContractUpdate) {
  return patch<SignalContractResponse>(`/contracts/${contractId}`, body);
}

/** DELETE /api/v1/contracts/:id */
export function deleteContract(contractId: string) {
  return del(`/contracts/${contractId}`);
}

/** POST /api/v1/contracts/:id/fetch */
export function triggerContractFetch(contractId: string) {
  return post<{ status: string; job_id: string; contract_id: string; contract_name: string }>(
    `/contracts/${contractId}/fetch`,
  );
}

/** POST /api/v1/contracts/:id/activate */
export function activateContract(contractId: string) {
  return post<SignalContractResponse>(`/contracts/${contractId}/activate`);
}

/** POST /api/v1/contracts/:id/deactivate */
export function deactivateContract(contractId: string) {
  return post<SignalContractResponse>(`/contracts/${contractId}/deactivate`);
}
