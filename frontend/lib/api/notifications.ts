/**
 * Notifications API service.
 *
 * Maps to: backend/api/v1/notifications.py
 */

import { get, patch, post } from './client';

export interface NotificationItem {
  id: string;
  type: 'signal' | 'contract' | 'system';
  title: string;
  body: string;
  created_at: string;
  unread: boolean;
}

export interface NotificationsResponse {
  items: NotificationItem[];
  unread_count: number;
}

export interface MarkReadResponse {
  updated: number;
}

/** GET /api/v1/notifications */
export function listNotifications(limit = 20) {
  return get<NotificationsResponse>('/notifications', {
    params: { limit },
  });
}

export function markNotificationRead(notificationId: string) {
  return patch<MarkReadResponse>(`/notifications/${notificationId}/read`);
}

export function markAllNotificationsRead() {
  return post<MarkReadResponse>('/notifications/mark-all-read');
}
