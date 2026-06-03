'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { requestsApi, TokenManager } from '@/lib/api';
import Link from 'next/link';

interface GDPRRequest {
  id: string;
  userId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  dataCategories: string[];
  requestedAt: string;
  expiresAt: string;
  completedAt: string | null;
  notes: string;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  processing: 'bg-blue-50 border-blue-200 text-blue-800',
  completed: 'bg-green-50 border-green-200 text-green-800',
  failed: 'bg-red-50 border-red-200 text-red-800',
  cancelled: 'bg-orange-50 border-orange-200 text-orange-800',
};

const statusLabels: Record<string, string> = {
  pending: 'Pendiente',
  processing: 'Procesando',
  completed: 'Completado',
  failed: 'Fallido',
  cancelled: 'Cancelado',
};

export default function RequestsPage() {
  const router = useRouter();
  const [requests, setRequests] = useState<GDPRRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const checkAuthAndLoadRequests = async () => {
      const authenticated = TokenManager.isAuthenticated();
      if (!authenticated) {
        router.push('/login');
        return;
      }

      setIsAuthenticated(true);

      try {
        const data = await requestsApi.list();
        setRequests(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading requests');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuthAndLoadRequests();
  }, [router]);

  const handleNewRequest = () => {
    router.push('/requests/new');
  };

  const handleLogout = () => {
    TokenManager.clearToken();
    router.push('/');
  };

  if (!isAuthenticated) {
    return null;
  }

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
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Mis solicitudes GDPR</h1>
            <p className="text-sm text-gray-600 mt-1">
              Gestiona tus solicitudes de acceso a datos personales
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="btn btn-secondary"
          >
            Cerrar sesión
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
        {/* Error Alert */}
        {error && (
          <div className="alert alert-error mb-6">
            {error}
          </div>
        )}

        {/* Action Button */}
        <div className="mb-8">
          <button
            onClick={handleNewRequest}
            className="btn btn-primary"
          >
            + Nueva solicitud GDPR
          </button>
        </div>

        {/* Requests Table */}
        {requests.length === 0 ? (
          <div className="card text-center py-12">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No tienes solicitudes aún
            </h3>
            <p className="text-gray-600 mb-6">
              Crea una nueva solicitud para acceder a tus datos personales
            </p>
            <button
              onClick={handleNewRequest}
              className="btn btn-primary"
            >
              Crear primera solicitud
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">
                    ID Solicitud
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">
                    Estado
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">
                    Fecha Solicitud
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">
                    Vence
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">
                    Acción
                  </th>
                </tr>
              </thead>
              <tbody>
                {requests.map((request) => (
                  <tr
                    key={request.id}
                    className="border-b border-gray-200 hover:bg-gray-50"
                  >
                    <td className="py-3 px-4 text-sm font-mono text-gray-600">
                      {request.id.slice(0, 8)}...
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-sm font-medium border alert ${statusColors[request.status]}`}
                      >
                        {statusLabels[request.status]}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {new Date(request.requestedAt).toLocaleDateString('es-ES')}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {new Date(request.expiresAt).toLocaleDateString('es-ES')}
                    </td>
                    <td className="py-3 px-4 text-sm">
                      <Link
                        href={`/requests/${request.id}`}
                        className="text-blue-600 hover:text-blue-700 font-medium"
                      >
                        Ver detalles
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {/* Footer Info */}
      <footer className="border-t border-gray-200 bg-gray-50 mt-auto">
        <div className="max-w-6xl mx-auto px-4 py-6 text-center text-xs text-gray-600">
          <p className="mb-2">
            Bajo GDPR Artículo 15, tienes derecho a acceder a tus datos personales.
          </p>
          <p>
            Tus solicitudes caducan después de 30 días. Por preguntas,{' '}
            <span className="font-medium text-gray-900">
              contacta a privacy@example.com
            </span>
          </p>
        </div>
      </footer>
    </div>
  );
}
