/**
 * Search & Synthesis API service.
 *
 * Maps to: backend/api/v1/search.py, backend/api/v1/synthesis.py
 */

import { get, post } from './client';
import type {
  SearchRequest,
  SearchResponse,
  SearchHistoryResponse,
  SynthesisRequest,
  SynthesisResponse,
} from './types';

/** POST /api/v1/search */
export function executeSearch(body: SearchRequest) {
  return post<SearchResponse>('/search', body);
}

/** GET /api/v1/search/history */
export function getSearchHistory(params?: { skip?: number; limit?: number }) {
  return get<SearchHistoryResponse>('/search/history', { params: params as Record<string, string | number | boolean | undefined> });
}

/** POST /api/v1/synthesis */
export function synthesize(body: SynthesisRequest) {
  return post<SynthesisResponse>('/synthesis', body);
}
