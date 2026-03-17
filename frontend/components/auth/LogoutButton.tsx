'use client';

/**
 * Logout Button Component
 * 
 * Logs user out and clears session
 */
export default function LogoutButton() {
  return (
    <a
      href="/api/auth/logout"
      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
    >
      Log Out
    </a>
  );
}
