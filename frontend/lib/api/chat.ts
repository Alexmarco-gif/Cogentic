/**
 * Chat API service.
 *
 * Maps to: backend/api/v1/chat.py
 */

import { get, post, patch, del, streamSSE, type SSECallbacks } from './client';
import type {
  ChatSessionResponse,
  ChatSessionDetailResponse,
  ChatSessionListResponse,
  CreateSessionRequest,
  SendMessageRequest,
  ChatDeleteResponse,
} from './types';

/** POST /api/v1/chat/sessions */
export function createChatSession(body?: CreateSessionRequest) {
  return post<ChatSessionResponse>('/chat/sessions', body);
}

/** GET /api/v1/chat/sessions */
export function listChatSessions(params?: { skip?: number; limit?: number }) {
  return get<ChatSessionListResponse>('/chat/sessions', { params: params as Record<string, string | number | boolean | undefined> });
}

/** GET /api/v1/chat/sessions/:id */
export function getChatSession(sessionId: string) {
  return get<ChatSessionDetailResponse>(`/chat/sessions/${sessionId}`);
}

/**
 * POST /api/v1/chat/sessions/:id/messages
 *
 * This endpoint returns an SSE stream, not a JSON response.
 * Use the callbacks to handle streaming events.
 *
 * Events: thinking, tool_call, tool_result, content, citation, recommendation, done, error
 */
export function sendChatMessage(
  sessionId: string,
  body: SendMessageRequest,
  callbacks: SSECallbacks,
) {
  return streamSSE(`/chat/sessions/${sessionId}/messages`, body, callbacks);
}

/** PATCH /api/v1/chat/sessions/:id/archive */
export function archiveChatSession(sessionId: string) {
  return patch<ChatSessionResponse>(`/chat/sessions/${sessionId}/archive`);
}

/** DELETE /api/v1/chat/sessions/:id */
export function deleteChatSession(sessionId: string) {
  return del<ChatDeleteResponse>(`/chat/sessions/${sessionId}`);
}
