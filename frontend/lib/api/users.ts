/**
 * Users API service.
 *
 * Maps to: backend/api/v1/users.py
 */

import { get, patch } from './client';
import type {
  UserProfileResponse,
  UserProfileUpdate,
} from './types';

/** GET /api/v1/users/me */
export function getMyProfile() {
  return get<UserProfileResponse>('/users/me');
}

/** PATCH /api/v1/users/me */
export function updateMyProfile(body: UserProfileUpdate) {
  return patch<UserProfileResponse>('/users/me', body);
}

/** GET /api/v1/users/:userId */
export function getUserProfile(userId: string) {
  return get<UserProfileResponse>(`/users/${userId}`);
}
