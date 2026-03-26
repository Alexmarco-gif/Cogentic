/**
 * Organizations API service.
 *
 * Maps to: backend/api/v1/orgs.py
 */

import { get, post, patch, del } from './client';
import type {
  OrganizationResponse,
  OrganizationUpdate,
  MemberListResponse,
  MemberResponse,
  AddMemberRequest,
  MemberRoleUpdate,
} from './types';

/** GET /api/v1/orgs/:orgId */
export function getOrganization(orgId: string) {
  return get<OrganizationResponse>(`/orgs/${orgId}`);
}

/** PATCH /api/v1/orgs/:orgId */
export function updateOrganization(orgId: string, body: OrganizationUpdate) {
  return patch<OrganizationResponse>(`/orgs/${orgId}`, body);
}

/** DELETE /api/v1/orgs/:orgId */
export function deleteOrganization(orgId: string) {
  return del(`/orgs/${orgId}`);
}

/** GET /api/v1/orgs/:orgId/members */
export function listMembers(orgId: string, params?: { skip?: number; limit?: number }) {
  return get<MemberListResponse>(`/orgs/${orgId}/members`, { params: params as Record<string, string | number | boolean | undefined> });
}

/** POST /api/v1/orgs/:orgId/members */
export function addMember(orgId: string, body: AddMemberRequest) {
  return post<MemberResponse>(`/orgs/${orgId}/members`, body);
}

/** PATCH /api/v1/orgs/:orgId/members/:userId */
export function updateMemberRole(orgId: string, userId: string, body: MemberRoleUpdate) {
  return patch<MemberResponse>(`/orgs/${orgId}/members/${userId}`, body);
}

/** DELETE /api/v1/orgs/:orgId/members/:userId */
export function removeMember(orgId: string, userId: string) {
  return del(`/orgs/${orgId}/members/${userId}`);
}
