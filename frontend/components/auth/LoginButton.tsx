'use client';

/**
 * Login Button Component
 * 
 * Redirects user to Auth0 Universal Login page
 */
export default function LoginButton() {
  return (
    <a
      href="/api/auth/login"
      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
    >
      Log In
    </a>
  );
}
