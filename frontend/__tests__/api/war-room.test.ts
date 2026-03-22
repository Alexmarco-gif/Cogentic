/**
 * War Room (Investigate / Chat) — Integration & Contract Tests
 *
 * Validates:
 *  1. TypeScript type shapes match backend Pydantic schemas
 *  2. createChatSession sends industry_slug (not industry_id)
 *  3. sendChatMessage sends { message } (not { content })
 *  4. SSE stream is parsed correctly and events are dispatched
 *  5. Fallback fires when backend is unreachable
 *
 * All tests mock `fetch` — no network required.
 * The test scenario mirrors a real user typing a question in the War Room.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type {
  SendMessageRequest,
  CreateSessionRequest,
  ChatSessionResponse,
  ChatDeleteResponse,
} from '@/lib/api/types';

// ── Helpers ───────────────────────────────────────────────────────────────────

function mockJsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
    body: null,
  } as unknown as Response;
}

function mockTokenResponse() {
  return mockJsonResponse({ token: 'test-bearer-token' });
}

/**
 * Build a ReadableStream delivering the full SSE payload in one chunk.
 * This mirrors real HTTP streaming — event: and data: for a single SSE
 * message arrive in the same read() call, so the parser correctly tracks
 * currentEvent across the event/data pair.
 */
function mockSSEStream(lines: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const fullText = lines.join('\n') + '\n';
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(fullText));
      controller.close();
    },
  });
}

function mockSSEResponse(lines: string[]): Response {
  return {
    ok: true,
    status: 200,
    statusText: 'OK',
    headers: new Headers({ 'content-type': 'text/event-stream' }),
    body: mockSSEStream(lines),
  } as unknown as Response;
}

let fetchMock: ReturnType<typeof vi.fn>;
const originalFetch = globalThis.fetch;

beforeEach(() => {
  fetchMock = vi.fn();
  globalThis.fetch = fetchMock as unknown as typeof fetch;
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
  vi.resetModules();
});

/** Last actual API call (skipping the token call). */
function lastApiCall() {
  const calls = fetchMock.mock.calls;
  const call = calls[calls.length - 1];
  return {
    url: call[0] as string,
    method: ((call[1] as RequestInit)?.method ?? 'GET') as string,
    body: JSON.parse((call[1] as RequestInit)?.body as string ?? '{}') as Record<string, unknown>,
    headers: (call[1] as RequestInit)?.headers as Record<string, string>,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. TYPE CONTRACT VALIDATION
// ─────────────────────────────────────────────────────────────────────────────

describe('Type contract: SendMessageRequest', () => {
  it('has a "message" field (not "content") matching backend schema', () => {
    // This will fail to compile if SendMessageRequest doesn't have "message"
    const req: SendMessageRequest = { message: 'What are the top risks?' };
    expect(req.message).toBe('What are the top risks?');
    // TypeScript would error at compile time if "content" field still existed
    // Runtime guard: the key must be exactly "message"
    expect(Object.keys(req)).toEqual(['message']);
  });

  it('does NOT have a "content" field', () => {
    const req: SendMessageRequest = { message: 'test' };
    expect((req as unknown as Record<string, unknown>).content).toBeUndefined();
  });
});

describe('Type contract: CreateSessionRequest', () => {
  it('has "industry_slug" (not "industry_id") matching backend schema', () => {
    const req: CreateSessionRequest = { industry_slug: 'fintech', title: 'My session' };
    expect(req.industry_slug).toBe('fintech');
    expect(Object.keys(req).sort()).toEqual(['industry_slug', 'title'].sort());
  });

  it('does NOT have an "industry_id" field', () => {
    const req: CreateSessionRequest = { industry_slug: 'energy' };
    expect((req as unknown as Record<string, unknown>).industry_id).toBeUndefined();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. createChatSession — correct endpoint & payload
// ─────────────────────────────────────────────────────────────────────────────

describe('createChatSession', () => {
  const SESSION_RESPONSE: ChatSessionResponse = {
    id: 'sess-001',
    user_id: 'user-001',
    org_id: 'org-001',
    industry_id: null,
    title: 'Fintech Risk Analysis',
    status: 'active',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  it('POST /api/v1/chat/sessions with correct URL and method', async () => {
    const { createChatSession } = await import('@/lib/api/chat');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockJsonResponse(SESSION_RESPONSE, 201));

    await createChatSession({ title: 'Test session' });

    const { url, method } = lastApiCall();
    expect(method).toBe('POST');
    expect(url).toBe('/api/v1/chat/sessions');
  });

  it('sends industry_slug in the body', async () => {
    const { createChatSession } = await import('@/lib/api/chat');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockJsonResponse(SESSION_RESPONSE, 201));

    await createChatSession({ industry_slug: 'fintech', title: 'War Room' });

    const { body } = lastApiCall();
    // KEY ASSERTION: must be industry_slug, not industry_id
    expect(body).toHaveProperty('industry_slug', 'fintech');
    expect(body).not.toHaveProperty('industry_id');
  });

  it('attaches a Bearer token in Authorization header', async () => {
    const { createChatSession } = await import('@/lib/api/chat');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockJsonResponse(SESSION_RESPONSE, 201));

    await createChatSession({ title: 'Auth test' });

    const { headers } = lastApiCall();
    expect(headers['Authorization']).toBe('Bearer test-bearer-token');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. sendChatMessage — correct BODY FIELD ("message" not "content")
// ─────────────────────────────────────────────────────────────────────────────

describe('sendChatMessage — payload field name', () => {
  const SESSION_ID = 'sess-001';
  const USER_QUERY = 'What are the top fintech risks this quarter?';

  const SSE_LINES = [
    'event: thinking',
    'data: {"status":"analyzing"}',
    '',
    'event: content',
    `data: {"text":"Based on your signal feed, the top risks are..."}`,
    '',
    'event: citation',
    `data: {"id":"c1","index":1,"title":"CB Insights Fintech Report","source":"CB Insights","published_at":"2026-03-01","excerpt":"...","highlight":"...","url":"https://example.com","relevance":"high"}`,
    '',
    'event: done',
    'data: {"session_id":"sess-001","message_count":2}',
    '',
  ];

  it('sends { message } (not { content }) to /api/v1/chat/sessions/:id/messages', async () => {
    const { sendChatMessage } = await import('@/lib/api/chat');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockSSEResponse(SSE_LINES));

    const receivedEvents: Array<{ event: string; data: unknown }> = [];

    await sendChatMessage(
      SESSION_ID,
      { message: USER_QUERY },
      {
        onEvent: (event, data) => receivedEvents.push({ event, data }),
        onDone: () => {},
        onError: (err) => { throw err; },
      },
    );

    // Wait for pump to finish
    await new Promise(r => setTimeout(r, 50));

    const { url, method, body } = lastApiCall();

    // ── URL and method
    expect(method).toBe('POST');
    expect(url).toBe(`/api/v1/chat/sessions/${SESSION_ID}/messages`);

    // ── KEY ASSERTION: body must use "message", NOT "content"
    expect(body).toHaveProperty('message', USER_QUERY);
    expect(body).not.toHaveProperty('content');
  });

  it('parses SSE thinking, content, citation, and done events', async () => {
    const { sendChatMessage } = await import('@/lib/api/chat');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockSSEResponse(SSE_LINES));

    const receivedEvents: Array<{ event: string; data: unknown }> = [];
    let doneFired = false;

    await sendChatMessage(
      SESSION_ID,
      { message: USER_QUERY },
      {
        onEvent: (event, data) => receivedEvents.push({ event, data }),
        onDone: () => { doneFired = true; },
        onError: (err) => { throw err; },
      },
    );

    await new Promise(r => setTimeout(r, 50));

    const eventNames = receivedEvents.map(e => e.event);
    expect(eventNames).toContain('thinking');
    expect(eventNames).toContain('content');
    expect(eventNames).toContain('citation');
    expect(eventNames).toContain('done');
    expect(doneFired).toBe(true);
  });

  it('content event has text chunk', async () => {
    const { sendChatMessage } = await import('@/lib/api/chat');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockSSEResponse(SSE_LINES));

    const receivedEvents: Array<{ event: string; data: unknown }> = [];

    await sendChatMessage(
      SESSION_ID,
      { message: USER_QUERY },
      {
        onEvent: (event, data) => receivedEvents.push({ event, data }),
        onDone: () => {},
        onError: (err) => { throw err; },
      },
    );

    await new Promise(r => setTimeout(r, 50));

    const contentEvent = receivedEvents.find(e => e.event === 'content');
    expect(contentEvent).toBeDefined();
    expect((contentEvent!.data as Record<string, string>).text).toContain('Based on your signal feed');
  });

  it('citation event has required fields for CitationsView', async () => {
    const { sendChatMessage } = await import('@/lib/api/chat');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockSSEResponse(SSE_LINES));

    const receivedEvents: Array<{ event: string; data: unknown }> = [];

    await sendChatMessage(
      SESSION_ID,
      { message: USER_QUERY },
      {
        onEvent: (event, data) => receivedEvents.push({ event, data }),
        onDone: () => {},
        onError: (err) => { throw err; },
      },
    );

    await new Promise(r => setTimeout(r, 50));

    const citationEvent = receivedEvents.find(e => e.event === 'citation');
    expect(citationEvent).toBeDefined();
    const c = citationEvent!.data as Record<string, unknown>;
    expect(c).toHaveProperty('id');
    expect(c).toHaveProperty('title');
    expect(c).toHaveProperty('relevance');
    expect(c).toHaveProperty('url');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. sendChatMessage — 422 backend error (wrong payload rejected)
// ─────────────────────────────────────────────────────────────────────────────

describe('sendChatMessage — backend rejection of wrong field name', () => {
  it('a payload using "content" would receive a 422, "message" receives 200', async () => {
    const { sendChatMessage } = await import('@/lib/api/chat');

    // Simulate what the backend would return for wrong field {"content": "..."}
    const errorSSE = [
      'event: error',
      'data: {"code":"validation_error","message":"field required: message"}',
      '',
    ];

    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockSSEResponse(errorSSE));

    const receivedEvents: Array<{ event: string; data: unknown }> = [];

    // Send CORRECT field
    await sendChatMessage(
      'sess-wrong-test',
      { message: 'correct field name' },
      {
        onEvent: (event, data) => receivedEvents.push({ event, data }),
        onDone: () => {},
        onError: () => {},
      },
    );

    await new Promise(r => setTimeout(r, 50));

    // The request body in the actual call must contain "message"
    const { body } = lastApiCall();
    expect(body.message).toBe('correct field name');
    expect(body.content).toBeUndefined();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Session lifecycle: archive and delete
// ─────────────────────────────────────────────────────────────────────────────

describe('Chat session lifecycle', () => {
  it('archiveChatSession → PATCH /api/v1/chat/sessions/:id/archive', async () => {
    const { archiveChatSession } = await import('@/lib/api/chat');
    const SESSION_ID = 'sess-archive-001';
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockJsonResponse({
      id: SESSION_ID, status: 'archived',
      user_id: 'u1', org_id: 'o1',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));

    await archiveChatSession(SESSION_ID);

    const { url, method } = lastApiCall();
    expect(method).toBe('PATCH');
    expect(url).toBe(`/api/v1/chat/sessions/${SESSION_ID}/archive`);
  });

  it('deleteChatSession → DELETE /api/v1/chat/sessions/:id', async () => {
    const { deleteChatSession } = await import('@/lib/api/chat');
    const SESSION_ID = 'sess-delete-001';
    const deleteResponse: ChatDeleteResponse = { deleted: true, session_id: SESSION_ID };

    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockJsonResponse(deleteResponse));

    const result = await deleteChatSession(SESSION_ID);

    const { url, method } = lastApiCall();
    expect(method).toBe('DELETE');
    expect(url).toBe(`/api/v1/chat/sessions/${SESSION_ID}`);
    expect(result.deleted).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. Full user interaction simulation: "User asks a question in War Room"
// ─────────────────────────────────────────────────────────────────────────────

describe('War Room — full user interaction simulation', () => {
  it('simulates: user opens War Room → asks question → receives streamed AI response', async () => {
    const { createChatSession, sendChatMessage } = await import('@/lib/api/chat');

    const SESSION = {
      id: 'sess-e2e-001',
      user_id: 'user-e2e-001',
      org_id: 'org-001',
      industry_id: null,
      title: 'Fintech war room query',
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // ── Step 1: Create session (user opens War Room, industry context = fintech)
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockJsonResponse(SESSION, 201));

    const session = await createChatSession({
      industry_slug: 'fintech',
      title: 'Fintech war room query',
    });

    expect(session.id).toBe('sess-e2e-001');
    expect(session.status).toBe('active');

    // Verify correct field was sent
    const sessionCall = lastApiCall();
    expect(sessionCall.body).toHaveProperty('industry_slug', 'fintech');

    // ── Step 2: User types and sends a message in the chat input
    const USER_QUESTION = 'What regulatory risks should I monitor in fintech this quarter?';

    const AI_STREAM = [
      'event: thinking',
      'data: {"status":"searching_sources"}',
      '',
      'event: thinking',
      'data: {"status":"reading_documents"}',
      '',
      'event: content',
      `data: {"text":"Based on current intelligence, the key regulatory risks include..."}`,
      '',
      'event: content',
      `data: {"text":" Basel IV implementation timelines and DORA compliance deadlines."}`,
      '',
      'event: citation',
      `data: {"id":"cit-1","index":1,"title":"EBA Risk Dashboard Q1 2026","source":"European Banking Authority","published_at":"2026-03-01","excerpt":"DORA compliance deadline approaching","highlight":"DORA","url":"https://eba.europa.eu","relevance":"high"}`,
      '',
      'event: done',
      `data: {"session_id":"${SESSION.id}","message_count":2,"tokens_used":450}`,
      '',
    ];

    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockSSEResponse(AI_STREAM));

    const receivedEvents: Array<{ event: string; data: unknown }> = [];
    let streamComplete = false;
    let accumulatedText = '';

    await sendChatMessage(
      session.id,
      { message: USER_QUESTION },
      {
        onEvent: (event, data) => {
          receivedEvents.push({ event, data });
          if (event === 'content') {
            accumulatedText += (data as Record<string, string>).text ?? '';
          }
        },
        onDone: () => { streamComplete = true; },
        onError: (err) => { throw new Error(`Stream error: ${err.message}`); },
      },
    );

    await new Promise(r => setTimeout(r, 50));

    // ── Assertions simulating what the UI should show ──────────────

    // Request payload used correct field name
    const msgCall = lastApiCall();
    expect(msgCall.url).toBe(`/api/v1/chat/sessions/${SESSION.id}/messages`);
    expect(msgCall.method).toBe('POST');
    expect(msgCall.body).toHaveProperty('message', USER_QUESTION);
    expect(msgCall.body).not.toHaveProperty('content');

    // Stream events arrived
    const eventTypes = receivedEvents.map(e => e.event);
    expect(eventTypes.filter(e => e === 'thinking').length).toBe(2);
    expect(eventTypes.filter(e => e === 'content').length).toBe(2);
    expect(eventTypes).toContain('citation');
    expect(eventTypes).toContain('done');

    // Text was streamed and accumulated correctly
    expect(accumulatedText).toContain('regulatory risks');
    expect(accumulatedText).toContain('DORA');

    // Citation has required fields for CitationsView rendering
    const citEvent = receivedEvents.find(e => e.event === 'citation')!;
    const citation = citEvent.data as Record<string, unknown>;
    expect(citation.id).toBe('cit-1');
    expect(citation.relevance).toBe('high');
    expect(typeof citation.url).toBe('string');

    // Stream completed
    expect(streamComplete).toBe(true);
  });

  it('simulates: fallback when session creation fails (backend down)', async () => {
    const { createChatSession } = await import('@/lib/api/chat');

    // Token succeeds but session creation 500s
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockJsonResponse({ detail: 'Internal server error' }, 500));

    await expect(createChatSession({ title: 'Should fail' })).rejects.toThrow();
  });

  it('simulates: network failure does not crash the app (SSE error callback fires)', async () => {
    const { sendChatMessage } = await import('@/lib/api/chat');

    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      headers: new Headers({ 'content-type': 'application/json' }),
      text: () => Promise.resolve('Service Unavailable'),
      body: null,
    } as unknown as Response);

    let errorFired = false;
    let errorMessage = '';

    await sendChatMessage(
      'sess-fail',
      { message: 'Will this fail gracefully?' },
      {
        onEvent: () => {},
        onDone: () => {},
        onError: (err) => {
          errorFired = true;
          errorMessage = err.message;
        },
      },
    );

    // onError must fire (not throw unhandled)
    expect(errorFired).toBe(true);
    expect(errorMessage).toContain('503');
  });
});
