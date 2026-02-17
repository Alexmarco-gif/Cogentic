import { NextRequest, NextResponse } from 'next/server';
import { 
  verifyHmacSignature, 
  verifyTimestamp, 
  isDuplicateEvent,
  parseAuth0Event,
  logWebhookEvent,
  type Auth0Event
} from '@/lib/webhook-utils';

// Import test event logger
let addWebhookEvent: ((event: any) => void) | null = null;
if (process.env.NODE_ENV === 'development') {
  import('../test/route').then((module) => {
    addWebhookEvent = module.addWebhookEvent;
  });
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

// Log event types we care about
const TRACKED_EVENTS = {
  ss: 'signup',           // Successful Signup
  s: 'login',             // Success Login
  spr: 'password_reset',  // Successful Password Reset
  sad: 'account_delete',  // Success Account Deletion
  f: 'failed_login',      // Failed Login (for security monitoring)
  fu: 'failed_signup',    // Failed Signup
};

/**
 * Handle user signup event
 */
async function handleSignup(event: any) {
  const userId = event.user_id;
  const email = event.details?.user_email || event.user_name;
  
  console.log(`[WEBHOOK] User signup: ${email} (${userId})`);
  
  // TODO: Create user record in database
  // TODO: Create personal organization for user
  // TODO: Send welcome email
  
  return {
    action: 'signup',
    userId,
    email,
    timestamp: event.date,
  };
}

/**
 * Handle user login event
 */
async function handleLogin(event: any) {
  const userId = event.user_id;
  const email = event.user_name;
  const ip = event.ip;
  
  console.log(`[WEBHOOK] User login: ${email} from ${ip}`);
  
  // TODO: Update last_login timestamp in database
  // TODO: Track login analytics
  // TODO: Check for suspicious login patterns
  
  return {
    action: 'login',
    userId,
    email,
    ip,
    timestamp: event.date,
  };
}

/**
 * Handle password reset event
 */
async function handlePasswordReset(event: any) {
  const userId = event.user_id;
  const email = event.user_name;
  
  console.log(`[WEBHOOK] Password reset: ${email}`);
  
  // TODO: Log security event
  // TODO: Notify user of password change
  // TODO: Invalidate existing sessions (optional)
  
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
  
  console.log(`[WEBHOOK] Account deletion: ${email}`);
  
  // TODO: Cascade delete user data
  // TODO: Remove from organizations
  // TODO: Archive data (GDPR compliance)
  
  return {
    action: 'account_delete',
    userId,
    email,
    timestamp: event.date,
  };
}

/**
 * Handle failed login (security monitoring)
 */
async function handleFailedLogin(event: any) {
  const email = event.user_name;
  const ip = event.ip;
  const reason = event.description;
  
  console.warn(`[WEBHOOK] Failed login: ${email} from ${ip} - ${reason}`);
  
  // TODO: Track failed login attempts
  // TODO: Implement rate limiting
  // TODO: Alert on brute force attempts
  
  return {
    action: 'failed_login',
    email,
    ip,
    reason,
    timestamp: event.date,
  };
}

/**
 * Handle failed signup (security monitoring)
 */
async function handleFailedSignup(event: any) {
  const email = event.user_name;
  const ip = event.ip;
  const reason = event.description;
  
  console.warn(`[WEBHOOK] Failed signup: ${email} from ${ip} - ${reason}`);
  
  // TODO: Track failed signup attempts
  // TODO: Implement rate limiting
  // TODO: Alert on suspicious patterns
  
  return {
    action: 'failed_signup',
    email,
    ip,
    reason,
    timestamp: event.date,
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
      console.log(`[WEBHOOK] Unhandled event type: ${eventType}`);
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
        console.error('[WEBHOOK] Missing signature header');
        return NextResponse.json(
          { error: 'Missing signature' },
          { status: 401 }
        );
      }
      
      const isValid = verifyHmacSignature(rawBody, signature, webhookSecret);
      if (!isValid) {
        console.error('[WEBHOOK] Invalid signature');
        return NextResponse.json(
          { error: 'Invalid signature' },
          { status: 401 }
        );
      }
    } else {
      if (process.env.NODE_ENV === 'production') {
        console.error('[WEBHOOK] CRITICAL: No webhook secret configured in production');
        return NextResponse.json(
          { error: 'Webhook verification not configured' },
          { status: 500 }
        );
      }
      console.warn('[WEBHOOK] ⚠️  No webhook secret configured - skipping verification (dev only)');
    }
    
    // Parse the event
    const event = JSON.parse(rawBody);
    
    // Auth0 may send test events
    if (event.type === 'test') {
      console.log('[WEBHOOK] Received test event');
      return NextResponse.json({ status: 'ok', message: 'Test received' });
    }
    
    // Check for duplicate events (idempotency)
    const eventId = `${event.type}_${event.date}_${event.user_id || 'system'}`;
    if (isDuplicateEvent(eventId)) {
      console.log(`[WEBHOOK] Duplicate event ignored: ${eventId}`);
      return NextResponse.json({ 
        status: 'ok', 
        message: 'Duplicate event ignored' 
      });
    }
    
    // Verify event timestamp (prevent replay attacks)
    const isRecentEvent = verifyTimestamp(event.date, 300); // 5 minutes
    if (!isRecentEvent) {
      console.warn(`[WEBHOOK] Event too old or timestamp invalid: ${event.date}`);
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
    console.error('[WEBHOOK] Error processing webhook:', error);
    
    // Log error event
    try {
      const event = JSON.parse(await request.text());
      const parsedEvent = parseAuth0Event(event);
      logWebhookEvent(
        parsedEvent, 
        'error', 
        error instanceof Error ? error.message : 'Unknown error'
      );
    } catch (parseError) {
      // Ignore parse errors in error handler
    }
    
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
