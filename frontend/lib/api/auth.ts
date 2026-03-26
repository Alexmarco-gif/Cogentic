/**
 * Auth API service.
 *
 * Maps to: backend/api/v1/auth.py
 */

import { get } from './client';
import type {
  CurrentUserResponse,
  PermissionsResponse,
  TokenVerifyResponse,
} from './types';

/** GET /api/v1/auth/me */
export function getCurrentUser() {
  return get<CurrentUserResponse>('/auth/me');
}

/** GET /api/v1/auth/permissions */
export function getPermissions() {
  return get<PermissionsResponse>('/auth/permissions');
}

/** GET /api/v1/auth/token/verify */
export function verifyToken() {
  return get<TokenVerifyResponse>('/auth/token/verify');
}
