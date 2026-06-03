'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { TokenManager } from '@/lib/api';
import Link from 'next/link';

export default function Home() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAuth = () => {
      const authenticated = TokenManager.isAuthenticated();
      const userData = TokenManager.getUser();

      setIsAuthenticated(authenticated);
      setUser(userData);
      setIsLoading(false);

      // Redirect to requests if already authenticated
      if (authenticated) {
        router.push('/requests');
      }
    };

    checkAuth();
  }, [router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin-slow text-blue-600">
          <svg
            className="w-12 h-12"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="max-w-md w-full animate-fade-in">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            GDPR Data Request
          </h1>
          <p className="text-gray-600">
            Request and manage your personal data under GDPR Article 15
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 gap-4 mb-8">
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              🔒 Secure & Private
            </h3>
            <p className="text-sm text-gray-600">
              All requests are encrypted and comply with GDPR regulations.
            </p>
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              ⚡ Fast Processing
            </h3>
            <p className="text-sm text-gray-600">
              Your data requests are processed quickly and securely.
            </p>
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              📥 Easy Download
            </h3>
            <p className="text-sm text-gray-600">
              Download your data in a portable, standardized format.
            </p>
          </div>
        </div>

        {/* CTA Buttons */}
        <div className="space-y-3">
          <Link
            href="/login"
            className="btn btn-primary w-full text-center block"
          >
            Sign In
          </Link>

          <Link
            href="/register"
            className="btn btn-secondary w-full text-center block"
          >
            Create Account
          </Link>
        </div>

        {/* Footer Info */}
        <div className="mt-8 pt-6 border-t border-gray-200 text-center text-sm text-gray-600">
          <p className="mb-2">
            Under GDPR Article 15, you have the right to access your personal
            data.
          </p>
          <p>
            For questions, contact{' '}
            <span className="font-medium text-gray-900">
              privacy@example.com
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
