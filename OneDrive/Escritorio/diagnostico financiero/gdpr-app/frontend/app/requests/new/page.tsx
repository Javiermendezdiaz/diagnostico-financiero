'use client';

import { useRouter } from 'next/navigation';
import { TokenManager } from '@/lib/api';
import RequestForm from '@/components/RequestForm';
import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function NewRequestPage() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const authenticated = TokenManager.isAuthenticated();
    if (!authenticated) {
      router.push('/login');
      return;
    }
    setIsAuthenticated(true);
  }, [router]);

  const handleSuccess = () => {
    router.push('/requests?success=true');
  };

  const handleError = (error: string) => {
    console.error('Request creation error:', error);
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <Link href="/requests" className="text-blue-600 hover:text-blue-700 text-sm font-medium mb-4 block">
            ← Volver a solicitudes
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">
            Nueva Solicitud GDPR
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Artículo 15 - Derecho a acceder a datos personales
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8">
        <div className="card">
          <RequestForm onSuccess={handleSuccess} onError={handleError} />
        </div>

        {/* Information Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-2">⏱️ Plazo de Respuesta</h3>
            <p className="text-sm text-gray-600">
              Procesamos tu solicitud dentro de 30 días naturales tal como exige la ley GDPR.
            </p>
          </div>

          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-2">🔒 Seguridad</h3>
            <p className="text-sm text-gray-600">
              Todos tus datos están encriptados y almacenados de forma segura con protocolos TLS.
            </p>
          </div>

          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-2">📥 Descarga</h3>
            <p className="text-sm text-gray-600">
              Una vez completada, descarga tus datos en formato ZIP estructurado.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-gray-50 mt-auto">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center text-xs text-gray-600">
          <p>
            Reglamento UE 2016/679 (GDPR) - Protección de datos personales
          </p>
        </div>
      </footer>
    </div>
  );
}
