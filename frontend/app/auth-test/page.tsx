import { getCurrentUser } from '@/lib/auth0';
import UserProfile from '@/components/auth/UserProfile';
import LoginButton from '@/components/auth/LoginButton';
import LogoutButton from '@/components/auth/LogoutButton';
import { DevGate } from '@/lib/dev-gate';

/**
 * Auth Test Page
 * 
 * Simple page to test Auth0 integration
 * - Login/Logout functionality
 * - User session display
 * - Custom JWT claims verification
 * 
 * ⚠️ Development Only - Not accessible in production
 */
export default async function AuthTestPage() {
  const user = await getCurrentUser();

  return (
    <DevGate>
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold mb-8 text-center">
          🔐 Auth0 Integration Test
        </h1>

        {/* Status Banner */}
        <div className={`p-4 rounded-lg mb-8 text-center ${
          user ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
        }`}>
          {user ? (
            <p className="font-semibold">✅ Authenticated</p>
          ) : (
            <p className="font-semibold">⚠️ Not authenticated - Click login to test</p>
          )}
        </div>

        {/* User Profile Card */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">User Session</h2>
          <UserProfile />
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 justify-center mb-8">
          {!user && <LoginButton />}
          {user && <LogoutButton />}
        </div>

        {/* Instructions */}
        <div className="bg-white p-6 rounded-lg shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Test Instructions</h2>
          <ol className="list-decimal list-inside space-y-2 text-gray-700">
            <li>Click "Log In" button above</li>
            <li>You'll be redirected to Auth0 Universal Login</li>
            <li>Sign in with email/password, Google, or GitHub</li>
            <li>After successful login, you'll return here</li>
            <li>Verify your user info and custom claims are displayed</li>
            <li>Click "Log Out" to end session</li>
          </ol>

          <div className="mt-6 p-4 bg-blue-50 rounded border border-blue-200">
            <h3 className="font-semibold text-blue-900 mb-2">What to Check:</h3>
            <ul className="list-disc list-inside space-y-1 text-sm text-blue-800">
              <li>User ID (sub) is present</li>
              <li>Email and name are correct</li>
              <li>Plan shows (default: free)</li>
              <li>Roles array exists (may be empty initially)</li>
              <li>org_id may be null (will be set by backend later)</li>
            </ul>
          </div>
        </div>

        {/* JWT Claims Debug (only show when authenticated) */}
        {user && (
          <div className="mt-8 bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs overflow-x-auto">
            <h3 className="text-white font-semibold mb-2">JWT Claims (Debug)</h3>
            <pre>{JSON.stringify(user, null, 2)}</pre>
          </div>
        )}

        {/* API Test Section */}
        <div className="mt-8 bg-white p-6 rounded-lg shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Next Steps</h2>
          <div className="space-y-2 text-gray-700">
            <p>✅ <strong>Phase 1.2 Complete</strong> if you can:</p>
            <ul className="list-disc list-inside ml-4 space-y-1">
              <li>Successfully log in</li>
              <li>See your user info displayed</li>
              <li>Custom claims (org_id, roles, plan) are in JWT</li>
              <li>Successfully log out</li>
            </ul>
            <p className="mt-4 text-blue-600 font-medium">
              → Ready for Phase 1.3: FastAPI Backend Integration
            </p>
          </div>
        </div>
      </div>
    </div>
    </DevGate>
  );
}
