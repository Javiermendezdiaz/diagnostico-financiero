'use client';

import { useState } from 'react';
import { requestsApi } from '@/lib/api';

interface RequestFormProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

export const DATA_CATEGORIES = [
  'Información Personal',
  'Información de Contacto',
  'Información Financiera',
  'Historial de Transacciones',
  'Registros de Comunicación',
  'Datos de Ubicación',
  'Información del Dispositivo',
  'Historial de Navegación',
];

export default function RequestForm({ onSuccess, onError }: RequestFormProps) {
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [notes, setNotes] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCategoryChange = (category: string) => {
    setSelectedCategories((prev) => {
      if (prev.includes(category)) {
        return prev.filter((c) => c !== category);
      } else {
        return [...prev, category];
      }
    });
  };

  const handleSelectAll = () => {
    if (selectedCategories.length === DATA_CATEGORIES.length) {
      setSelectedCategories([]);
    } else {
      setSelectedCategories([...DATA_CATEGORIES]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (selectedCategories.length === 0) {
      const msg = 'Selecciona al menos una categoría de datos';
      setError(msg);
      onError?.(msg);
      return;
    }

    setIsLoading(true);

    try {
      await requestsApi.create(selectedCategories, notes);
      setSelectedCategories([]);
      setNotes('');
      onSuccess?.();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error creating request';
      setError(msg);
      onError?.(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Error Alert */}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Categories Section */}
      <div>
        <h3 className="label">Categorías de Datos</h3>
        <p className="text-sm text-gray-600 mb-4">
          Selecciona las categorías de datos personales que deseas acceder:
        </p>

        {/* Select All Checkbox */}
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={selectedCategories.length === DATA_CATEGORIES.length}
              onChange={handleSelectAll}
              className="w-4 h-4 text-blue-600 cursor-pointer"
              disabled={isLoading}
            />
            <span className="ml-3 font-medium text-blue-900">
              Seleccionar todas las categorías
            </span>
          </label>
        </div>

        {/* Categories Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {DATA_CATEGORIES.map((category) => (
            <label
              key={category}
              className="flex items-start p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
            >
              <input
                type="checkbox"
                checked={selectedCategories.includes(category)}
                onChange={() => handleCategoryChange(category)}
                className="w-4 h-4 text-blue-600 mt-0.5 cursor-pointer"
                disabled={isLoading}
              />
              <span className="ml-3 text-gray-700">{category}</span>
            </label>
          ))}
        </div>

        {/* Selected Count */}
        <p className="text-xs text-gray-500 mt-3">
          {selectedCategories.length} de {DATA_CATEGORIES.length} categorías
          seleccionadas
        </p>
      </div>

      {/* Notes Section */}
      <div>
        <label htmlFor="notes" className="label">
          Notas Adicionales (Opcional)
        </label>
        <textarea
          id="notes"
          className="input resize-none"
          placeholder="Añade cualquier nota o comentario sobre tu solicitud..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          disabled={isLoading}
          rows={4}
        />
        <p className="text-xs text-gray-500 mt-2">
          Máximo 500 caracteres
        </p>
      </div>

      {/* Legal Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-900">
        <p className="mb-2">
          <strong>Aviso Legal:</strong> Al enviar esta solicitud:
        </p>
        <ul className="list-disc list-inside space-y-1 text-blue-800">
          <li>Reconoces tu derecho bajo GDPR Artículo 15</li>
          <li>Tu solicitud será procesada dentro de 30 días naturales</li>
          <li>La privacidad de tus datos está garantizada mediante encriptación</li>
          <li>Se generará un registro de auditoría de esta solicitud</li>
        </ul>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        className="btn btn-primary w-full"
        disabled={isLoading || selectedCategories.length === 0}
      >
        {isLoading ? 'Procesando solicitud...' : 'Enviar Solicitud GDPR'}
      </button>
    </form>
  );
}
