// frontend/components/RequestCard.tsx
import React from 'react';
import Link from 'next/link';
import { DataRequest, RequestStatus } from '@/types';
import clsx from 'clsx';

interface RequestCardProps {
  request: DataRequest;
}

const getStatusBadgeColor = (status: RequestStatus): string => {
  const colors = {
    pending: '#FDD731',       // amarillo (Adapta)
    processing: '#4A90E2',    // azul
    completed: '#16A766',     // verde
    cancelled: '#E74C3C',     // rojo
    failed: '#E74C3C',        // rojo
  };
  return colors[status];
};

const getStatusLabel = (status: RequestStatus): string => {
  const labels = {
    pending: 'Pendiente',
    processing: 'En proceso',
    completed: 'Completado',
    cancelled: 'Cancelado',
    failed: 'Error',
  };
  return labels[status];
};

const formatDate = (timestamp: number): string => {
  return new Date(timestamp).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatDaysRemaining = (estimatedDate: number): string => {
  const today = Date.now();
  const daysLeft = Math.ceil((estimatedDate - today) / (1000 * 60 * 60 * 24));

  if (daysLeft < 0) return 'Vencido';
  if (daysLeft === 0) return 'Hoy';
  if (daysLeft === 1) return 'Mañana';
  return `${daysLeft} días`;
};

export const RequestCard: React.FC<RequestCardProps> = ({ request }) => {
  const statusColor = getStatusBadgeColor(request.status);
  const statusLabel = getStatusLabel(request.status);
  const daysRemaining = formatDaysRemaining(request.estimatedCompletionDate);

  return (
    <Link href={`/request/${request.requestId}`}>
      <a style={{ textDecoration: 'none' }}>
        <div
          style={{
            border: '1px solid #CCCCCC',
            borderRadius: '8px',
            padding: '20px',
            marginBottom: '16px',
            backgroundColor: '#FFFFFF',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
          }}
          onMouseOver={(e) => {
            (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)';
          }}
          onMouseOut={(e) => {
            (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)';
            (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
          }}
        >
          {/* Header: Nombre + Badge Estado */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '12px',
            }}
          >
            <h3
              style={{
                margin: 0,
                fontSize: '16px',
                fontWeight: '600',
                color: '#020203',
              }}
            >
              {request.requesterName}
            </h3>
            <div
              style={{
                backgroundColor: statusColor,
                color: request.status === 'pending' ? '#020203' : '#FFFFFF',
                padding: '6px 12px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: '600',
              }}
            >
              {statusLabel}
            </div>
          </div>

          {/* Email + Tipo solicitante */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '12px',
              marginBottom: '12px',
              fontSize: '13px',
              color: '#666666',
            }}
          >
            <div>
              <span style={{ fontWeight: '600' }}>Email:</span> {request.requesterEmail}
            </div>
            <div>
              <span style={{ fontWeight: '600' }}>Tipo:</span> {request.requesterType}
            </div>
          </div>

          {/* Categorías de datos */}
          {request.dataCategories && request.dataCategories.length > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <span style={{ fontWeight: '600', fontSize: '12px', color: '#020203' }}>
                Categorías:
              </span>
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '6px',
                  marginTop: '6px',
                }}
              >
                {request.dataCategories.map((category, idx) => (
                  <span
                    key={idx}
                    style={{
                      backgroundColor: '#FAF8F3',
                      border: '1px solid #FDD731',
                      color: '#343434',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                    }}
                  >
                    {category}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Fechas */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '12px',
              fontSize: '12px',
              color: '#666666',
              borderTop: '1px solid #EEEEEE',
              paddingTop: '12px',
            }}
          >
            <div>
              <span style={{ fontWeight: '600' }}>Fecha solicitud:</span>
              <br />
              {formatDate(request.requestDate)}
            </div>
            <div>
              <span style={{ fontWeight: '600' }}>Vencimiento estimado:</span>
              <br />
              {daysRemaining}
            </div>
          </div>

          {/* Pie: Botón de acción rápida */}
          <div
            style={{
              marginTop: '12px',
              paddingTop: '12px',
              borderTop: '1px solid #EEEEEE',
              fontSize: '12px',
            }}
          >
            <span style={{ color: '#FDD731', fontWeight: '600' }}>Ver detalle →</span>
          </div>
        </div>
      </a>
    </Link>
  );
};
