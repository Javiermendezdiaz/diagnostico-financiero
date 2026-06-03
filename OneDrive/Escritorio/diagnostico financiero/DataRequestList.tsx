import React, { useState, useCallback } from 'react';
import { useDataRequests } from '@/hooks/useDataRequests';
import { DataRequestRow } from './DataRequestRow';
import { DataRequestButton } from './DataRequestButton';
import { ConfirmationModal } from './ConfirmationModal';
import { useAutoDownload } from './useAutoDownload';
import { analytics } from './analytics.service';
import styles from './DataRequestList.module.css';

const requestTypeLabels: Record<string, string> = {
  access: 'Acceso a datos',
  deletion: 'Eliminación',
  portability: 'Portabilidad',
};

/**
 * DataRequestList — Fase 3: Enhanced UX
 * GDPR Art. 15, 17, 20 with ConfirmationModal, auto-download, analytics
 */
export const DataRequestList: React.FC = () => {
  const { requests, loading, error, downloadExport, cancelRequest, startPolling } =
    useDataRequests();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Modal state for Art. 17 deletion confirmation
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    type: 'cancel' | 'delete' | null;
    requestId: string | null;
  }>({
    isOpen: false,
    type: null,
    requestId: null,
  });

  const [isProcessing, setIsProcessing] = useState(false);

  // Auto-download on completion
  const completedRequest = requests.find(r => r.status === 'completed' && r.id === modalState.requestId);
  useAutoDownload(completedRequest || null, downloadExport, {
    enabled: true,
    onDownloadStart: () => {
      setSuccessMessage('Descargando datos...');
    },
    onDownloadComplete: (filename) => {
      analytics.trackExportDownloaded(completedRequest!.id, filename);
      setSuccessMessage(`Descargado: ${filename}`);
      setTimeout(() => setSuccessMessage(null), 5000);
    },
    onDownloadError: (error) => {
      analytics.trackError('DOWNLOAD_FAILED', error.message, { request_id: completedRequest?.id });
      setSuccessMessage(`Error: ${error.message}`);
      setTimeout(() => setSuccessMessage(null), 5000);
    },
  });

  const handleDownload = useCallback(async (requestId: string) => {
    try {
      await downloadExport(requestId);
      const request = requests.find(r => r.id === requestId);
      if (request) {
        analytics.trackExportDownloaded(requestId, `data_export_${Date.now()}.json`);
      }
      setSuccessMessage('Descarga iniciada correctamente');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      analytics.trackError('DOWNLOAD_FAILED', error.message, { request_id: requestId });
      console.error('[DataRequestList] Download error:', error);
      setSuccessMessage(null);
    }
  }, [requests, downloadExport]);

  const handleCancelRequest = useCallback(
    (requestId: string, type: 'cancel' | 'delete') => {
      setModalState({
        isOpen: true,
        type,
        requestId,
      });
    },
    []
  );

  const handleConfirmCancel = useCallback(async () => {
    const { requestId, type } = modalState;
    if (!requestId) return;

    try {
      setIsProcessing(true);
      await cancelRequest(requestId);

      analytics.trackRequestCancelled(requestId);
      setSuccessMessage('Solicitud cancelada correctamente');
      setTimeout(() => setSuccessMessage(null), 3000);

      setModalState({ isOpen: false, type: null, requestId: null });
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      analytics.trackError('CANCEL_FAILED', error.message, { request_id: requestId });
      console.error('[DataRequestList] Cancel error:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [modalState, cancelRequest]);

  const handleCloseModal = useCallback(() => {
    setModalState({ isOpen: false, type: null, requestId: null });
  }, []);

  if (loading && requests.length === 0) {
    return (
      <div className={styles.dataRequestList}>
        <div className={styles.spinner}>
          <div className={styles.spinnerInner}></div>
          <p>Cargando solicitudes...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.dataRequestList}>
        <div className={styles.errorBanner} role="alert">
          <span className={styles.errorIcon}>⚠️</span>
          <div>
            <p className={styles.errorTitle}>Error al cargar solicitudes</p>
            <p className={styles.errorMessage}>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.dataRequestList}>
      {/* Header */}
      <div className={styles.header}>
        <h2>Solicitudes de datos</h2>
        <p className={styles.subtitle}>
          Solicita acceso, eliminación o portabilidad de tus datos según GDPR
        </p>
      </div>

      {/* Action Buttons */}
      <div className={styles.actionsBar}>
        <DataRequestButton requestType="access" />
        <DataRequestButton requestType="deletion" />
        <DataRequestButton requestType="portability" />
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className={styles.successBanner} role="status">
          <span className={styles.successIcon}>✓</span>
          {successMessage}
        </div>
      )}

      {/* Requests Table or Empty State */}
      {requests.length === 0 ? (
        <div className={styles.empty}>
          <p>No hay solicitudes de datos pendientes</p>
          <p className={styles.emptyHint}>
            Usa los botones arriba para crear una nueva solicitud
          </p>
        </div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">Tipo de solicitud</th>
                <th scope="col">Creada</th>
                <th scope="col">Estado</th>
                <th scope="col">Expira</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <DataRequestRow
                  key={request.id}
                  request={request}
                  requestTypeLabel={requestTypeLabels[request.request_type] || request.request_type}
                  onDownload={handleDownload}
                  onCancel={() => handleCancelRequest(request.id, request.request_type === 'deletion' ? 'delete' : 'cancel')}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Compliance Notice */}
      <div className={styles.complianceNotice}>
        <span className={styles.noticeIcon}>ⓘ</span>
        <div className={styles.noticeContent}>
          <p className={styles.noticeTitle}>Tus derechos GDPR</p>
          <p className={styles.noticeBody}>
            Puedes solicitar acceso (Art. 15), eliminación (Art. 17) o portabilidad (Art. 20) de tus
            datos personales. Las solicitudes se procesan en un máximo de 30 días. Todos los datos
            descargados expirarán después de 30 días.
          </p>
          <p className={styles.noticeArticle}>Art. 15, 17, 20 GDPR</p>
        </div>
      </div>

      {/* ConfirmationModal — Art. 17 Deletion */}
      <ConfirmationModal
        isOpen={modalState.isOpen}
        title={
          modalState.type === 'delete'
            ? '¿Eliminar solicitud? (Art. 17)'
            : '¿Cancelar solicitud?'
        }
        message={
          modalState.type === 'delete'
            ? 'Esta acción no se puede deshacer. Todos tus datos serán permanentemente eliminados del servidor.'
            : 'La solicitud será cancelada y no se continuará procesando.'
        }
        confirmText={
          modalState.type === 'delete'
            ? 'Sí, eliminar permanentemente'
            : 'Sí, cancelar'
        }
        cancelText="Atrás"
        variant={modalState.type === 'delete' ? 'danger' : 'warning'}
        onConfirm={handleConfirmCancel}
        onCancel={handleCloseModal}
        isLoading={isProcessing}
        disabled={isProcessing}
      />
    </div>
  );
};
