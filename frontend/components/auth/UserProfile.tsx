import { getCurrentUser } from '@/lib/auth0';
import Image from 'next/image';

/**
 * User Profile Component (Server Component)
 * 
 * Displays current user info and custom claims
 * Shows login button if not authenticated
 */
export default async function UserProfile() {
  const user = await getCurrentUser();

  if (!user) {
    return (
      <div className="p-4 bg-gray-100 rounded-lg">
        <p className="text-gray-600 mb-4">Not logged in</p>
        <a
          href="/api/auth/login"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 inline-block"
        >
          Log In
        </a>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white border rounded-lg shadow-sm">
      <div className="flex items-center gap-4 mb-4">
        {user.picture && (
          <Image
            src={user.picture}
            alt={user.name || 'User'}
            width={64}
            height={64}
            className="rounded-full"
          />
        )}
        <div>
          <h3 className="text-lg font-semibold">{user.name || 'User'}</h3>
          <p className="text-sm text-gray-600">{user.email}</p>
        </div>
      </div>

      <div className="space-y-2 text-sm">
        <div>
          <span className="font-medium">User ID:</span>{' '}
          <code className="text-xs bg-gray-100 px-2 py-1 rounded">{user.sub}</code>
        </div>
        
        {user.org_id && (
          <div>
            <span className="font-medium">Organization:</span>{' '}
            <code className="text-xs bg-gray-100 px-2 py-1 rounded">{user.org_id}</code>
          </div>
        )}

        <div>
          <span className="font-medium">Plan:</span>{' '}
          <span className={`text-xs px-2 py-1 rounded ${
            user.plan === 'enterprise' ? 'bg-purple-100 text-purple-800' :
            user.plan === 'pro' ? 'bg-blue-100 text-blue-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {user.plan.toUpperCase()}
          </span>
        </div>

        <div>
          <span className="font-medium">Roles:</span>{' '}
          {user.roles.length > 0 ? (
            <div className="flex gap-1 mt-1">
              {user.roles.map(role => (
                <span
                  key={role}
                  className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded"
                >
                  {role}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-gray-500">None</span>
          )}
        </div>
      </div>

      <div className="mt-4">
        <a
          href="/api/auth/logout"
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 inline-block text-sm"
        >
          Log Out
        </a>
      </div>
    </div>
  );
}
