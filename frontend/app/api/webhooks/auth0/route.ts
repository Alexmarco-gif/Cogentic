import { NextRequest, NextResponse } from 'next/server';
import crypto from 'crypto';
import {
  verifyHmacSignature,
  verifyDirectToken,
  verifyTimestamp,
  isDuplicateEvent,
  parseAuth0Event,
  logWebhookEvent,
  type Auth0Event
} from '@/lib/webhook-utils';
import { addWebhookEvent } from '@/lib/webhookStore';

/**
 * Thrown when a critical lifecycle event fails to sync to the backend.
 * Caught in the POST handler to return HTTP 502 instead of 200.
 */
class BackendForwardError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'BackendForwardError';
  }
}

/**
 * Auth0 Webhook Handler
 *
 * Receives events from Auth0 Log Streams:
 * - User signup (ss - Successful Signup)
 * - User login (s - Success Login)
 * - Password reset (spr - Successful Password Reset)
 * - Account deletion (sad - Success Account Deletion)
 *
 * Webhook URL: https://yourdomain.com/api/webhooks/auth0
 */

// ── Structured logger (server-side only) ─────────────────────────────────────

function log(level: 'info' | 'warn' | 'error', event: string, data?: Record<string, unknown>) {
  const entry = JSON.stringify({ ts: new Date().toISOString(), level, event, ...data });
  if (level === 'error') process.stderr.write(entry + '\n');
  else process.stdout.write(entry + '\n');
}

// Log event types we care about
const TRACKED_EVENTS = {
  ss: 'signup',           // Successful Signup
  s: 'login',             // Success Login
  spr: 'password_reset',  // Successful Password Reset
  sad: 'account_delete',  // Success Account Deletion
  f: 'failed_login',      // Failed Login (for security monitoring)
  fu: 'failed_signup',    // Failed Signup
};

// Map Auth0 Log Stream event types to backend webhook event types
const EVENT_TYPE_MAP: Record<string, string> = {
  ss: 'post-registration',
  s: 'post-login',
  sad: 'post-user-deletion',
};

/**
 * Forward a processed event to the backend webhook handler.
 *
 * Signs the payload with the shared AUTH0_WEBHOOK_SECRET so the backend's
 * HMAC verification passes, then POSTs to /webhooks/auth0/events.
 */
async function forwardToBackend(
  payload: Record<string, unknown>
): Promise<{ success: boolean; data?: any; error?: string }> {
  const backendUrl =
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://localhost:8000';
  const webhookSecret = process.env.AUTH0_WEBHOOK_SECRET;

  const body = JSON.stringify(payload);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Sign the payload so the backend's verify_webhook_signature passes
  if (webhookSecret) {
    const signature = crypto
      .createHmac('sha256', webhookSecret)
      .update(body)
      .digest('hex');
    headers['X-Auth0-Signature'] = `sha256=${signature}`;
  }

  try {
    const response = await fetch(`${backendUrl}/webhooks/auth0/events`, {
      method: 'POST',
      headers,
      body,
      signal: AbortSignal.timeout(10_000), // 10 s timeout
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: data.detail || `Backend returned ${response.status}`,
      };
    }

    return { success: true, data };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to forward to backend',
    };
  }
}

// ── In-memory security tracking ──────────────────────────────────────────────
// Tracks failed login/signup attempts per IP for brute-force detection.
// In a multi-replica deployment, replace with Redis counters.
const failedLoginTracker = new Map<string, number>();

// Purge stale entries every 15 minutes to prevent memory leaks
setInterval(() => {
  failedLoginTracker.clear();
}, 15 * 60 * 1000).unref();

/**
 * Handle user signup event
 */
async function handleSignup(event: any) {
  const userId = event.user_id;
  const email = event.details?.user_email || event.user_name;
  const name = event.details?.user_name || event.user_name?.split('@')[0];
  const picture = event.details?.user_picture;

  log('info', 'webhook_signup', { userId, email: email ? '[REDACTED]' : undefined });

  // Forward to backend — creates user record + personal organization
  const backendPayload = {
    event: 'post-registration',
    user_id: userId,
    email,
    name,
    picture,
    created_at: event.date,
    timestamp: event.date,
  };

  const result = await forwardToBackend(backendPayload);

  if (!result.success) {
    log('error', 'webhook_signup_forward_failed', { userId, error: result.error });
    throw new BackendForwardError(
      `Backend user-creation sync failed for ${userId}: ${result.error}`
    );
  } else {
    log('info', 'webhook_signup_forwarded', { userId, status: result.data?.status });
  }

  return {
    action: 'signup',
    userId,
    email,
    timestamp: event.date,
    backendResult: result.data,
  };
}

/**
 * Handle user login event
 */
async function handleLogin(event: any) {
  const userId = event.user_id;
  const email = event.user_name;
  const ip = event.ip;

  log('info', 'webhook_login', { userId, ip });

  // Forward to backend — updates last_login_at + login_count
  const backendPayload = {
    event: 'post-login',
    user_id: userId,
    email,
    timestamp: event.date,
  };

  const result = await forwardToBackend(backendPayload);

  if (!result.success) {
    log('warn', 'webhook_login_forward_failed', { userId, error: result.error });
  }

  return {
    action: 'login',
    userId,
    email,
    ip,
    timestamp: event.date,
    backendResult: result.data,
  };
}

/**
 * Handle password reset event
 */
async function handlePasswordReset(event: any) {
  const userId = event.user_id;
  const email = event.user_name;

  log('info', 'webhook_password_reset', { userId });

  // Password resets are security-noteworthy but don't require backend DB changes.
  // Log the event for audit trail and monitoring.
  log('info', 'webhook_password_reset_logged', {
    userId,
    ip: event.ip,
    date: event.date,
  });

  return {
    action: 'password_reset',
    userId,
    email,
    timestamp: event.date,
  };
}

/**
 * Handle account deletion event
 */
async function handleAccountDelete(event: any) {
  const userId = event.user_id;
  const email = event.user_name;

  log('info', 'webhook_account_delete', { userId });

  // Forward to backend — soft-deletes user and cascades to org memberships
  const backendPayload = {
    event: 'post-user-deletion',
    user_id: userId,
    email,
    timestamp: event.date,
  };

  const result = await forwardToBackend(backendPayload);

  if (!result.success) {
    log('error', 'webhook_account_delete_forward_failed', { userId, error: result.error });
    throw new BackendForwardError(
      `Backend account-deletion sync failed for ${userId}: ${result.error}`
    );
  } else {
    log('info', 'webhook_account_delete_forwarded', { userId, status: result.data?.status });
  }

  return {
    action: 'account_delete',
    userId,
    email,
    timestamp: event.date,
    backendResult: result.data,
  };
}

/**
 * Handle failed login (security monitoring)
 */
async function handleFailedLogin(event: any) {
  const email = event.user_name;
  const ip = event.ip;
  const reason = event.description;

  log('warn', 'webhook_failed_login', { ip, reason });

  // Track failed login attempts for brute-force detection.
  // Uses in-memory store; for production scale, consider Redis counters.
  const key = `failed_login:${ip}`;
  const count = failedLoginTracker.get(key) || 0;
  failedLoginTracker.set(key, count + 1);

  // Alert on potential brute-force (>10 failures from same IP)
  if (count + 1 >= 10) {
    log('error', 'webhook_brute_force_detected', {
      ip,
      attempts: count + 1,
      email,
    });
  }

  return {
    action: 'failed_login',
    email,
    ip,
    reason,
    timestamp: event.date,
    failedAttempts: count + 1,
  };
}

/**
 * Handle failed signup (security monitoring)
 */
async function handleFailedSignup(event: any) {
  const email = event.user_name;
  const ip = event.ip;
  const reason = event.description;

  log('warn', 'webhook_failed_signup', { ip, reason });

  // Track failed signup attempts for abuse detection
  const key = `failed_signup:${ip}`;
  const count = failedLoginTracker.get(key) || 0;
  failedLoginTracker.set(key, count + 1);

  // Alert on suspicious signup patterns (>5 from same IP)
  if (count + 1 >= 5) {
    log('error', 'webhook_signup_abuse_detected', {
      ip,
      attempts: count + 1,
    });
  }

  return {
    action: 'failed_signup',
    email,
    ip,
    reason,
    timestamp: event.date,
    failedAttempts: count + 1,
  };
}

/**
 * Process webhook event
 */
async function processEvent(event: any) {
  const eventType = event.type;

  switch (eventType) {
    case 'ss':
      return await handleSignup(event);
    case 's':
      return await handleLogin(event);
    case 'spr':
      return await handlePasswordReset(event);
    case 'sad':
      return await handleAccountDelete(event);
    case 'f':
      return await handleFailedLogin(event);
    case 'fu':
      return await handleFailedSignup(event);
    default:
      log('info', 'webhook_unhandled', { type: eventType });
      return { action: 'ignored', type: eventType };
  }
}

/**
 * POST /api/webhooks/auth0
 *
 * Receives webhook events from Auth0 Log Streams
 */
export async function POST(request: NextRequest) {
  try {
    // Get raw body for signature verification
    const rawBody = await request.text();

    // Verify signature if webhook secret is configured
    const webhookSecret = process.env.AUTH0_WEBHOOK_SECRET;
    const signature = request.headers.get('authorization')?.replace('Bearer ', '') ||
                      request.headers.get('x-auth0-signature');

    if (webhookSecret) {
      if (!signature) {
        log('error', 'webhook_missing_signature');
        return NextResponse.json(
          { error: 'Missing signature' },
          { status: 401 }
        );
      }

      // Auth0 Log Streams sends `Authorization: Bearer <token>` (static token
      // mode) or `X-Auth0-Signature: sha256=<hex>` (HMAC mode).  Try HMAC
      // first; fall back to constant-time bearer-token comparison.
      const sigValue = signature.startsWith('sha256=')
        ? signature.slice(7)
        : signature;

      const isValid =
        verifyHmacSignature(rawBody, sigValue, webhookSecret) ||
        verifyDirectToken(signature, webhookSecret);

      if (!isValid) {
        log('error', 'webhook_invalid_signature');
        return NextResponse.json(
          { error: 'Invalid signature' },
          { status: 401 }
        );
      }
    } else {
      if (process.env.NODE_ENV === 'production') {
        log('error', 'webhook_no_secret_in_production');
        return NextResponse.json(
          { error: 'Webhook verification not configured' },
          { status: 500 }
        );
      }
      log('warn', 'webhook_no_secret_dev');
    }

    // Parse the event
    const event = JSON.parse(rawBody);

    // Auth0 may send test events
    if (event.type === 'test') {
      log('info', 'webhook_test_event');
      return NextResponse.json({ status: 'ok', message: 'Test received' });
    }

    // Check for duplicate events (idempotency)
    const eventId = `${event.type}_${event.date}_${event.user_id || 'system'}`;
    if (isDuplicateEvent(eventId)) {
      log('info', 'webhook_duplicate', { eventId });
      return NextResponse.json({
        status: 'ok',
        message: 'Duplicate event ignored'
      });
    }

    // Verify event timestamp (prevent replay attacks)
    const isRecentEvent = verifyTimestamp(event.date, 300); // 5 minutes
    if (!isRecentEvent) {
      log('warn', 'webhook_stale_event', { date: event.date });
      return NextResponse.json(
        { error: 'Event timestamp invalid or too old' },
        { status: 400 }
      );
    }

    // Process the event
    const result = await processEvent(event);

    // Log event for monitoring
    const parsedEvent = parseAuth0Event(event);
    logWebhookEvent(parsedEvent, 'success');

    // Log event for testing (dev only)
    if (addWebhookEvent && process.env.NODE_ENV === 'development') {
      addWebhookEvent(event);
    }

    // Return success
    return NextResponse.json({
      status: 'ok',
      processed: result,
    });

  } catch (error) {
    // Critical backend sync failure — tell Auth0 to retry delivery
    if (error instanceof BackendForwardError) {
      log('error', 'webhook_backend_sync_failed', {
        message: error.message,
      });
      return NextResponse.json(
        { error: 'Backend sync failed', details: error.message },
        { status: 502 }
      );
    }

    log('error', 'webhook_processing_error', {
      message: error instanceof Error ? error.message : 'Unknown error',
    });

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * GET /api/webhooks/auth0
 *
 * Health check endpoint
 */
export async function GET() {
  return NextResponse.json({
    status: 'ok',
    message: 'Auth0 webhook endpoint is active',
    timestamp: new Date().toISOString(),
  });
}
