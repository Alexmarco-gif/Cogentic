import { getSession } from '@/auth0/nextjs-auth0';
import { getCurrentUser } from '@/lib/auth0';
import { DevGate } from '@/lib/dev-gate';

/**
 * JWT Token Inspector
 *
 * Displays raw JWT tokens and decoded claims for verification
 * Use this to verify Stage 1.3 custom claims implementation
 *
 * ⚠️ Development Only - Not accessible in production
 */
export default async function JWTTestPage() {
  const session = await getSession();
  const user = await getCurrentUser();

  // Decode JWT helper (client-safe, just parsing base64)
  const decodeJWT = (token: string) => {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return null;

      const payload = JSON.parse(
        Buffer.from(parts[1], 'base64').toString('utf-8')
      );
      return payload;
    } catch (e) {
      return null;
    }
  };

  const accessToken = session?.accessToken as string | undefined;
  const idToken = session?.idToken as string | undefined;

  const decodedAccess = accessToken ? decodeJWT(accessToken) : null;
  const decodedId = idToken ? decodeJWT(idToken) : null;

  // Check for custom claims
  const customClaimsNamespace = 'https://cogent.ai/claims';
  const hasOrgId = decodedAccess?.[`${customClaimsNamespace}/org_id`] !== undefined;
  const hasRoles = decodedAccess?.[`${customClaimsNamespace}/roles`] !== undefined;
  const hasPlan = decodedAccess?.[`${customClaimsNamespace}/plan`] !== undefined;

  if (!session || !user) {
    return (
      <DevGate>
      <div className="min-h-screen bg-gray-50 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">🔍 JWT Token Inspector</h1>

          <div className="bg-yellow-100 border border-yellow-400 text-yellow-800 p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-2">⚠️ Not Authenticated</h2>
            <p className="mb-4">You need to log in first to inspect JWT tokens.</p>
            <a
              href="/api/auth/login"
              className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Log In
            </a>
          </div>

          <div className="mt-8 bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">About This Tool</h2>
            <p className="text-gray-700 mb-4">
              This JWT inspector helps you verify Stage 1.3 implementation:
            </p>
            <ul className="list-disc list-inside space-y-2 text-gray-700">
              <li>View raw access tokens and ID tokens</li>
              <li>Decode and inspect token claims</li>
              <li>Verify custom claims are present</li>
              <li>Check token expiration and metadata</li>
            </ul>
          </div>
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
          <h1 className="text-3xl font-bold mb-2">🔍 JWT Token Inspector</h1>
          <p className="text-gray-600">Stage 1.3 Verification Tool</p>
        </div>

        {/* Status Banner */}
        <div className={`p-6 rounded-lg mb-8 ${
          hasOrgId && hasRoles && hasPlan
            ? 'bg-green-100 border-2 border-green-500'
            : 'bg-red-100 border-2 border-red-500'
        }`}>
          <h2 className="text-2xl font-bold mb-4">
            {hasOrgId && hasRoles && hasPlan ? '✅ Stage 1.3 COMPLETE!' : '❌ Custom Claims Missing'}
          </h2>

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className={hasOrgId ? 'text-green-700' : 'text-red-700'}>
                {hasOrgId ? '✅' : '❌'}
              </span>
              <code className="text-sm bg-white px-2 py-1 rounded">
                {customClaimsNamespace}/org_id
              </code>
              <span className="text-sm">
                {hasOrgId ? '(Present)' : '(Missing - Check Auth0 Action)'}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className={hasRoles ? 'text-green-700' : 'text-red-700'}>
                {hasRoles ? '✅' : '❌'}
              </span>
              <code className="text-sm bg-white px-2 py-1 rounded">
                {customClaimsNamespace}/roles
              </code>
              <span className="text-sm">
                {hasRoles ? '(Present)' : '(Missing - Check Auth0 Action)'}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className={hasPlan ? 'text-green-700' : 'text-red-700'}>
                {hasPlan ? '✅' : '❌'}
              </span>
              <code className="text-sm bg-white px-2 py-1 rounded">
                {customClaimsNamespace}/plan
              </code>
              <span className="text-sm">
                {hasPlan ? '(Present)' : '(Missing - Check Auth0 Action)'}
              </span>
            </div>
          </div>

          {!(hasOrgId && hasRoles && hasPlan) && (
            <div className="mt-4 p-4 bg-white rounded border border-red-300">
              <p className="font-semibold text-red-800 mb-2">Action Required:</p>
              <ol className="list-decimal list-inside space-y-1 text-sm text-red-700">
                <li>Go to Auth0 Dashboard → Actions → Library</li>
                <li>Verify "Add Custom Claims" Action is deployed</li>
                <li>Go to Actions → Flows → Login</li>
                <li>Ensure Action is between Start and Complete</li>
                <li>Add metadata to test user (see instructions below)</li>
                <li>Logout and login again to get new token</li>
              </ol>
            </div>
          )}
        </div>

        {/* User Info Summary */}
        <div className="bg-white p-6 rounded-lg shadow mb-8">
          <h2 className="text-xl font-semibold mb-4">👤 Current User</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-600">Email:</span>
              <p className="text-gray-900">{user.email}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">User ID:</span>
              <p className="text-gray-900 font-mono text-xs">{user.sub}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Organization ID:</span>
              <p className="text-gray-900 font-mono text-xs">
                {user.org_id || <span className="text-red-500">null</span>}
              </p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Plan:</span>
              <p className="text-gray-900">{user.plan}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Roles:</span>
              <p className="text-gray-900">
                {user.roles.length > 0 ? user.roles.join(', ') : <span className="text-gray-400">None</span>}
              </p>
            </div>
          </div>
        </div>

        {/* Access Token */}
        <div className="bg-white p-6 rounded-lg shadow mb-8">
          <h2 className="text-xl font-semibold mb-4">🎫 Access Token</h2>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Raw Token (truncated for display):
            </label>
            <div className="bg-gray-100 p-3 rounded font-mono text-xs break-all">
              {accessToken ? `${accessToken.substring(0, 100)}...` : 'No access token'}
            </div>
          </div>

          {decodedAccess && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Decoded Payload:
              </label>
              <pre className="bg-gray-900 text-green-400 p-4 rounded text-xs overflow-x-auto">
                {JSON.stringify(decodedAccess, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* ID Token */}
        <div className="bg-white p-6 rounded-lg shadow mb-8">
          <h2 className="text-xl font-semibold mb-4">🪪 ID Token</h2>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Raw Token (truncated for display):
            </label>
            <div className="bg-gray-100 p-3 rounded font-mono text-xs break-all">
              {idToken ? `${idToken.substring(0, 100)}...` : 'No ID token'}
            </div>
          </div>

          {decodedId && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Decoded Payload:
              </label>
              <pre className="bg-gray-900 text-green-400 p-4 rounded text-xs overflow-x-auto">
                {JSON.stringify(decodedId, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Token Metadata */}
        {decodedAccess && (
          <div className="bg-white p-6 rounded-lg shadow mb-8">
            <h2 className="text-xl font-semibold mb-4">📊 Token Metadata</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-600">Issuer:</span>
                <p className="text-gray-900 font-mono text-xs">{decodedAccess.iss}</p>
              </div>
              <div>
                <span className="font-medium text-gray-600">Audience:</span>
                <p className="text-gray-900 font-mono text-xs">{decodedAccess.aud}</p>
              </div>
              <div>
                <span className="font-medium text-gray-600">Issued At:</span>
                <p className="text-gray-900">
                  {new Date(decodedAccess.iat * 1000).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="font-medium text-gray-600">Expires At:</span>
                <p className="text-gray-900">
                  {new Date(decodedAccess.exp * 1000).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="font-medium text-gray-600">Subject:</span>
                <p className="text-gray-900 font-mono text-xs">{decodedAccess.sub}</p>
              </div>
              <div>
                <span className="font-medium text-gray-600">Scope:</span>
                <p className="text-gray-900 text-xs">{decodedAccess.scope}</p>
              </div>
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 p-6 rounded-lg mb-8">
          <h2 className="text-xl font-semibold text-blue-900 mb-4">
            📝 How to Add Metadata to Test User
          </h2>
          <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
            <li>Go to Auth0 Dashboard → <strong>User Management</strong> → <strong>Users</strong></li>
            <li>Find your test user: <code className="bg-white px-2 py-1 rounded">{user.email}</code></li>
            <li>Click on the user to open details</li>
            <li>Scroll to <strong>Metadata</strong> section</li>
            <li>Click <strong>Edit</strong> on <code className="bg-white px-2 py-1 rounded">app_metadata</code></li>
            <li>Paste this JSON:
              <pre className="bg-white p-3 rounded mt-2 text-xs overflow-x-auto">
{`{
  "org_id": "org_test_123",
  "roles": ["member"],
  "plan": "free"
}`}
              </pre>
            </li>
            <li>Click <strong>Save</strong></li>
            <li>Logout and login again to see updated claims</li>
          </ol>
        </div>

        {/* Actions */}
        <div className="flex gap-4 justify-center">
          <a
            href="/api/auth/logout"
            className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium"
          >
            Logout & Test Again
          </a>
          <a
            href="/auth-test"
            className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-medium"
          >
            Go to Auth Test Page
          </a>
        </div>
      </div>
    </div>
    </DevGate>
  );
}
