import React, { useState } from 'react';
import { useDataRequests } from '@/hooks/useDataRequests';
import styles from './DataRequestList.module.css';

interface DataRequestButtonProps {
  requestType: 'access' | 'deletion' | 'portability';
  label?: string;
  className?: string;
  onRequestCreated?: (requestId: string) => void;
}

const requestTypeLabels: Record<string, string> = {
  access: 'Solicitar acceso a datos',
  deletion: 'Solicitar eliminación',
  portability: 'Solicitar portabilidad',
};

const requestTypeDescriptions: Record<string, string> = {
  access: 'Art. 15 GDPR — Derecho de acceso',
  deletion: 'Art. 17 GDPR — Derecho al olvido',
  portability: 'Art. 20 GDPR — Derecho a la portabilidad',
};

/**
 * DataRequestButton — GDPR Art. 15, 17, 20
 *
 * Trigger button for data request creation (access, deletion, portability).
 * Handles loading state and error handling.
 *
 * Usage:
 * ```tsx
 * const { requestDataAccess } = useDataRequests();
 * <DataRequestButton requestType="access" />
 * ```
 */
export const DataRequestButton: React.FC<DataRequestButtonProps> = ({
  requestType,
  label,
  className,
  onRequestCreated,
}) => {
  const { loading, requestDataAccess, requestDeletion, requestPortability } =
    useDataRequests();
  const [localError, setLocalError] = useState<string | null>(null);

  const handleClick = async () => {
    setLocalError(null);
    try {
      let request;
      switch (requestType) {
        case 'access':
          request = await requestDataAccess();
          break;
        case 'deletion':
          request = await requestDeletion();
          break;
        case 'portability':
          request = await requestPortability();
          break;
      }
      if (onRequestCreated) {
        onRequestCreated(request.id);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Fallo al crear solicitud';
      setLocalError(message);
      console.error(`[DataRequestButton] Error creating ${requestType} request:`, err);
    }
  };

  return (
    <div className={className}>
      <button
        onClick={handleClick}
        disabled={loading}
        className={styles.buttonRequest}
        title={requestTypeDescriptions[requestType]}
        aria-label={label || requestTypeLabels[requestType]}
      >
        {loading ? (
          <>
            <span className={styles.spinnerSmall}></span>
            {' Procesando...'}
          </>
        ) : (
          label || requestTypeLabels[requestType]
        )}
      </button>
      {localError && (
        <p className={styles.errorSmall} role="alert">
          {localError}
        </p>
      )}
    </div>
  );
};
