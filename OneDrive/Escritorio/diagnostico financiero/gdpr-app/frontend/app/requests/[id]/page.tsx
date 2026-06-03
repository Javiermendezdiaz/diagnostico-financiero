'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
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

const statusDescriptions: Record<string, string> = {
  pending: 'Tu solicitud ha sido recibida y está esperando ser procesada.',
  processing: 'Estamos recopilando y preparando tus datos personales.',
  completed: 'Tu archivo está listo para descargar. Disponible por 30 días.',
  failed: 'No pudimos completar esta solicitud. Contacta con soporte.',
  cancelled: 'Esta solicitud ha sido cancelada.',
};

export default function RequestDetailPage() {
  const router = useRouter();
  const params = useParams();
  const requestId = params.id as string;

  const [request, setRequest] = useState<GDPRRequest | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const checkAuthAndLoadRequest = async () => {
      const authenticated = TokenManager.isAuthenticated();
      if (!authenticated) {
        router.push('/login');
        return;
      }

      setIsAuthenticated(true);

      try {
        const data = await requestsApi.getById(requestId);
        setRequest(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading request');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuthAndLoadRequest();
  }, [requestId, router]);

  const handleDownload = async () => {
    if (!request || request.status !== 'completed') {
      setError('Los datos no están listos para descargar');
      return;
    }

    setIsDownloading(true);
    setError('');

    try {
      const blob = await requestsApi.download(requestId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `GDPR_Data_${requestId}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error downloading data');
    } finally {
      setIsDownloading(false);
    }
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

  if (!request) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-4">
        <div className="card max-w-md text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Solicitud no encontrada
          </h2>
          <p className="text-gray-600 mb-6">
            La solicitud que buscas no existe o no tienes permiso para verla.
          </p>
          <Link href="/requests" className="btn btn-primary">
            Volver a mis solicitudes
          </Link>
        </div>
      </div>
    );
  }

  const isExpired = new Date(request.expiresAt) < new Date();
  const daysRemaining = Math.ceil(
    (new Date(request.expiresAt).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)
  );

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <Link
            href="/requests"
            className="text-blue-600 hover:text-blue-700 text-sm font-medium mb-4 block"
          >
            ← Volver a solicitudes
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">
            Detalles de la Solicitud
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8">
        {/* Error Alert */}
        {error && <div className="alert alert-error mb-6">{error}</div>}

        {/* Status Card */}
        <div className="card mb-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Estado de la Solicitud
              </h2>
              <span
                className={`inline-block px-4 py-2 rounded-full font-medium border alert ${statusColors[request.status]}`}
              >
                {statusLabels[request.status]}
              </span>
            </div>
            <div className="text-right text-sm">
              <p className="text-gray-600">ID: {request.id}</p>
            </div>
          </div>

          <p className="text-gray-700 mb-4">
            {statusDescriptions[request.status]}
          </p>

          {/* Expiration Notice */}
          {!isExpired && request.status !== 'completed' && request.status !== 'failed' && request.status !== 'cancelled' && (
            <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-900">
              <strong>Vencimiento:</strong> {daysRemaining} días restantes (
              {new Date(request.expiresAt).toLocaleDateString('es-ES')})
            </div>
          )}

          {isExpired && (
            <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-900">
              <strong>Expirada:</strong> Esta solicitud venció el{' '}
              {new Date(request.expiresAt).toLocaleDateString('es-ES')}
            </div>
          )}
        </div>

        {/* Request Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Timeline */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">📅 Cronología</h3>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-600">SOLICITUD REALIZADA</p>
                <p className="font-medium text-gray-900">
                  {new Date(request.requestedAt).toLocaleDateString('es-ES', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600">VENCIMIENTO</p>
                <p className="font-medium text-gray-900">
                  {new Date(request.expiresAt).toLocaleDateString('es-ES', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </p>
              </div>
              {request.completedAt && (
                <div>
                  <p className="text-xs text-gray-600">COMPLETADA</p>
                  <p className="font-medium text-gray-900">
                    {new Date(request.completedAt).toLocaleDateString('es-ES', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Data Categories */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">📋 Categorías de Datos</h3>
            <ul className="space-y-2">
              {request.dataCategories.map((category) => (
                <li key={category} className="flex items-center text-gray-700">
                  <span className="w-2 h-2 bg-blue-600 rounded-full mr-3"></span>
                  {category}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Notes Section */}
        {request.notes && (
          <div className="card mb-6">
            <h3 className="font-semibold text-gray-900 mb-2">📝 Notas</h3>
            <p className="text-gray-700 whitespace-pre-wrap">{request.notes}</p>
          </div>
        )}

        {/* Download Section */}
        {request.status === 'completed' && (
          <div className="card bg-gradient-to-br from-green-50 to-blue-50 border-2 border-green-200">
            <div className="flex items-center mb-4">
              <div className="text-4xl mr-4">📦</div>
              <div>
                <h3 className="font-semibold text-gray-900">Tus datos están listos</h3>
                <p className="text-sm text-gray-600">
                  Descargable como archivo ZIP comprimido
                </p>
              </div>
            </div>

            <button
              onClick={handleDownload}
              disabled={isDownloading}
              className="btn btn-primary w-full"
            >
              {isDownloading ? '⏳ Descargando...' : '⬇️ Descargar tus datos'}
            </button>

            <p className="text-xs text-gray-600 mt-4">
              El archivo contiene todos tus datos en formato estructurado y accesible.
              Este enlace expira en 7 días.
            </p>
          </div>
        )}

        {/* Legal Footer */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-6 text-xs text-gray-600">
          <p className="mb-2">
            <strong>Derecho de acceso (GDPR Artículo 15):</strong>
          </p>
          <ul className="list-disc list-inside space-y-1 text-gray-700">
            <li>Tienes derecho a acceder a tus datos personales</li>
            <li>Tu solicitud es procesada dentro de 30 días naturales</li>
            <li>Tus datos están protegidos con encriptación de nivel industrial</li>
            <li>Esta solicitud se registra para propósitos de auditoría GDPR</li>
          </ul>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-gray-50 mt-auto">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center text-xs text-gray-600">
          <p>
            Si tienes dudas sobre tu solicitud, contacta a{' '}
            <span className="font-medium text-gray-900">privacy@example.com</span>
          </p>
        </div>
      </footer>
    </div>
  );
}
