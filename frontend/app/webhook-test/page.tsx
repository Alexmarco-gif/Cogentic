'use client';

import { useState, useEffect } from 'react';
import { DevGate } from '@/lib/dev-gate';

/**
 * Webhook Test Page
 * 
 * View recent webhook events for debugging
 * 
 * ⚠️ Development Only - Not accessible in production
 */

interface WebhookEvent {
  type: string;
  date: string;
  user_id?: string;
  user_name?: string;
  ip?: string;
  description?: string;
  receivedAt: string;
}

export default function WebhookTestPage() {
  const [events, setEvents] = useState<WebhookEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchEvents = async () => {
    try {
      const response = await fetch('/api/webhooks/test');
      const data = await response.json();
      setEvents(data.events || []);
    } catch (error) {
      console.error('Failed to fetch webhook events:', error);
    } finally {
      setLoading(false);
    }
  };

  const clearEvents = async () => {
    try {
      await fetch('/api/webhooks/test', { method: 'DELETE' });
      setEvents([]);
    } catch (error) {
      console.error('Failed to clear events:', error);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchEvents, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const getEventBadgeColor = (type: string) => {
    switch (type) {
      case 'ss': return 'bg-green-100 text-green-800';
      case 's': return 'bg-blue-100 text-blue-800';
      case 'spr': return 'bg-yellow-100 text-yellow-800';
      case 'sad': return 'bg-red-100 text-red-800';
      case 'f': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getEventLabel = (type: string) => {
    const labels: Record<string, string> = {
      ss: 'Signup',
      s: 'Login',
      spr: 'Password Reset',
      sad: 'Account Delete',
      f: 'Failed Login',
      fu: 'Failed Signup',
    };
    return labels[type] || type;
  };

  if (loading) {
    return (
      <DevGate>
      <div className="min-h-screen bg-gray-50 py-12 px-4">
        <div className="max-w-6xl mx-auto">
          <p className="text-center text-gray-600">Loading webhook events...</p>
        </div>
      </div>
      </DevGate>
    );
  }

  return (
    <DevGate>
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">🔗 Webhook Event Monitor</h1>
          <p className="text-gray-600">
            Recent webhook events received from Auth0 (last 50)
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white p-4 rounded-lg shadow mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={fetchEvents}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              🔄 Refresh
            </button>
            
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Auto-refresh (3s)</span>
            </label>

            <div className="text-sm text-gray-600">
              Total events: <strong>{events.length}</strong>
            </div>
          </div>

          <button
            onClick={clearEvents}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
          >
            🗑️ Clear All
          </button>
        </div>

        {/* Events List */}
        {events.length === 0 ? (
          <div className="bg-white p-12 rounded-lg shadow text-center">
            <p className="text-gray-500 text-lg mb-4">No webhook events received yet</p>
            <div className="space-y-2 text-sm text-gray-600">
              <p>To generate events:</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Configure Auth0 Log Stream (see docs)</li>
                <li>Log in or sign up to your app</li>
                <li>Events will appear here automatically</li>
              </ol>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {events.map((event, index) => (
              <div
                key={index}
                className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold ${getEventBadgeColor(
                        event.type
                      )}`}
                    >
                      {getEventLabel(event.type)}
                    </span>
                    <span className="text-sm text-gray-500">
                      {new Date(event.receivedAt).toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  {event.user_name && (
                    <div>
                      <span className="font-medium text-gray-600">Email:</span>
                      <p className="text-gray-900">{event.user_name}</p>
                    </div>
                  )}

                  {event.user_id && (
                    <div>
                      <span className="font-medium text-gray-600">User ID:</span>
                      <p className="text-gray-900 font-mono text-xs">
                        {event.user_id}
                      </p>
                    </div>
                  )}

                  {event.ip && (
                    <div>
                      <span className="font-medium text-gray-600">IP Address:</span>
                      <p className="text-gray-900">{event.ip}</p>
                    </div>
                  )}

                  {event.description && (
                    <div className="col-span-2">
                      <span className="font-medium text-gray-600">Description:</span>
                      <p className="text-gray-900">{event.description}</p>
                    </div>
                  )}
                </div>

                {/* Raw Event (Collapsed) */}
                <details className="mt-4">
                  <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-900">
                    Show raw event data
                  </summary>
                  <pre className="mt-2 bg-gray-900 text-green-400 p-4 rounded text-xs overflow-x-auto">
                    {JSON.stringify(event, null, 2)}
                  </pre>
                </details>
              </div>
            ))}
          </div>
        )}

        {/* Instructions */}
        <div className="mt-8 bg-blue-50 border border-blue-200 p-6 rounded-lg">
          <h2 className="text-xl font-semibold text-blue-900 mb-4">
            📝 Setup Instructions
          </h2>
          <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
            <li>
              <strong>Install ngrok</strong>: Download from{' '}
              <a
                href="https://ngrok.com/download"
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                ngrok.com/download
              </a>
            </li>
            <li>
              <strong>Start ngrok</strong>: Run{' '}
              <code className="bg-white px-2 py-1 rounded">ngrok http 3000</code>
            </li>
            <li>
              <strong>Copy ngrok URL</strong>: Example:{' '}
              <code className="bg-white px-2 py-1 rounded">
                https://abc123.ngrok.io
              </code>
            </li>
            <li>
              <strong>Configure Auth0</strong>: Monitoring → Streams → Create Custom
              Webhook
            </li>
            <li>
              <strong>Set webhook URL</strong>:{' '}
              <code className="bg-white px-2 py-1 rounded">
                https://your-ngrok-url.ngrok.io/api/webhooks/auth0
              </code>
            </li>
            <li>
              <strong>Select events</strong>: s, ss, f, fu, spr, sad
            </li>
            <li>
              <strong>Test</strong>: Login/signup to trigger events
            </li>
          </ol>

          <div className="mt-4 p-4 bg-white rounded border border-blue-200">
            <p className="text-sm text-blue-900">
              <strong>📖 Full setup guide:</strong>{' '}
              <code>docs/auth/webhooks-setup.md</code>
            </p>
          </div>
        </div>
      </div>
    </div>
    </DevGate>
  );
}
