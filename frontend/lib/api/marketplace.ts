/**
 * Signal Marketplace API service.
 *
 * Maps to: backend/api/v1/marketplace.py
 */

import { del, get, post } from './client';
import type { SignalTemplateListResponse, SignalTemplateResponse, SubscribeResponse } from './types';

export interface ListTemplatesParams {
  country?: string;
  industry_id?: string;
  signal_type?: string;
  tag?: string;
  search?: string;
  featured_only?: boolean;
  skip?: number;
  limit?: number;
}

/** GET /api/v1/marketplace */
export function listTemplates(params?: ListTemplatesParams) {
  return get<SignalTemplateListResponse>('/marketplace', {
    params: params as Record<string, string | number | boolean | undefined>,
  });
}

/** GET /api/v1/marketplace/subscriptions */
export function listSubscriptions() {
  return get<SignalTemplateResponse[]>('/marketplace/subscriptions');
}

/** GET /api/v1/marketplace/:templateId */
export function getTemplate(templateId: string) {
  return get<SignalTemplateResponse>(`/marketplace/${templateId}`);
}

/** POST /api/v1/marketplace/subscribe */
export function subscribeToTemplate(templateId: string) {
  return post<SubscribeResponse>('/marketplace/subscribe', { template_id: templateId });
}

/** DELETE /api/v1/marketplace/subscribe/:templateId */
export function unsubscribeFromTemplate(templateId: string) {
  return del<void>(`/marketplace/subscribe/${templateId}`);
}
