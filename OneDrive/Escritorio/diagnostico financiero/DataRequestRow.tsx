import React, { useMemo } from 'react';
import styles from './DataRequestList.module.css';

export interface DataRequest {
  id: string;
  request_type: 'access' | 'deletion' | 'portability';
  status: 'pending' | 'processing' | 'completed' | 'rejected';
  created_at: string;
  completed_at: string | null;
  result_url: string | null;
  error_message: string | null;
  expires_at: string;
}

interface DataRequestRowProps {
  request: DataRequest;
  requestTypeLabel: string;
  onDownload: (requestId: string) => Promise<void>;
  onCancel: (requestId: string) => Promise<void>;
}

const getStatusBadge = (
  status: string
): { label: string; className: string } => {
  switch (status) {
    case 'pending':
      return { label: 'En espera', className: styles.statusPending };
    case 'processing':
      return { label: 'Procesando', className: styles.statusProcessing };
    case 'completed':
      return { label: 'Disponible', className: styles.statusCompleted };
    case 'rejected':
      return { label: 'Rechazada', className: styles.statusRejected };
    default:
      return { label: status, className: '' };
  }
};

const formatDate = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return dateString;
  }
};

const getDaysUntilExpiration = (expiresAt: string): number => {
  try {
    const expiration = new Date(expiresAt);
    const now = new Date();
    const diffTime = expiration.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return Math.max(0, diffDays);
  } catch {
    return 0;
  }
};

/**
 * DataRequestRow — Individual Data Request Display
 *
 * Renders a single data request with status badge, dates, and action buttons.
 * Shows countdown to expiration and download button when completed.
 *
 * Usage:
 * ```tsx
 * <DataRequestRow
 *   request={dataRequest}
 *   requestTypeLabel="Acceso a datos"
 *   onDownload={downloadHandler}
 *   onCancel={cancelHandler}
 * />
 * ```
 */
export const DataRequestRow: React.FC<DataRequestRowProps> = ({
  request,
  requestTypeLabel,
  onDownload,
  onCancel,
}) => {
  const badge = getStatusBadge(request.status);
  const daysLeft = useMemo(
    () => getDaysUntilExpiration(request.expires_at),
    [request.expires_at]
  );

  const canDownload = request.status === 'completed' && request.result_url;
  const canCancel = request.status === 'pending' || request.status === 'processing';

  const handleDownload = async () => {
    try {
      await onDownload(request.id);
    } catch (err) {
      console.error('[DataRequestRow] Download error:', err);
    }
  };

  const handleCancel = async () => {
    try {
      await onCancel(request.id);
    } catch (err) {
      console.error('[DataRequestRow] Cancel error:', err);
    }
  };

  return (
    <tr className={styles.tableRow}>
      <td className={styles.cellType}>{requestTypeLabel}</td>
      <td className={styles.cellDate}>{formatDate(request.created_at)}</td>
      <td>
        <span className={`${styles.badge} ${badge.className}`}>
          {badge.label}
        </span>
      </td>
      <td className={styles.cellExpiration}>
        {daysLeft > 0 ? (
          <span
            className={
              daysLeft <= 3 ? styles.expirationUrgent : styles.expirationNormal
            }
          >
            Expira en {daysLeft} {daysLeft === 1 ? 'día' : 'días'}
          </span>
        ) : (
          <span className={styles.expirationExpired}>Expirada</span>
        )}
      </td>
      <td className={styles.cellActions}>
        {canDownload ? (
          <button
            onClick={handleDownload}
            className={styles.buttonDownload}
            title="Descargar datos exportados"
            aria-label="Descargar datos exportados"
          >
            Descargar
          </button>
        ) : null}
        {canCancel ? (
          <button
            onClick={handleCancel}
            className={styles.buttonCancel}
            title="Cancelar solicitud"
            aria-label="Cancelar solicitud"
          >
            Cancelar
          </button>
        ) : null}
        {!canDownload && !canCancel ? <span className={styles.actionNone}>—</span> : null}
      </td>
    </tr>
  );
};
