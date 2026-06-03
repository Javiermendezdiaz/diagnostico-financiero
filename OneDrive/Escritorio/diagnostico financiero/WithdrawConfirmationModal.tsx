import React, { useEffect } from 'react';
import { ConsentRecord } from '@/hooks/useDataRights';
import styles from './ConsentManager.module.css';

interface WithdrawConfirmationModalProps {
  isOpen: boolean;
  consent: ConsentRecord | undefined;
  consentLabel: string;
  isWithdrawing: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const WithdrawConfirmationModal: React.FC<WithdrawConfirmationModalProps> = ({
  isOpen,
  consent,
  consentLabel,
  isWithdrawing,
  onConfirm,
  onCancel,
}) => {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen || !consent) return null;

  const formatDate = (date: string) => {
    return new Intl.DateTimeFormat('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(new Date(date));
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={styles.modalBackdrop}
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className={styles.modal}
        role="alertdialog"
        aria-labelledby="withdraw-title"
        aria-describedby="withdraw-description"
      >
        <div className={styles.modalContent}>
          {/* Header */}
          <div className={styles.modalHeader}>
            <h3 id="withdraw-title" className={styles.modalTitle}>
              ¿Revocar consentimiento?
            </h3>
            <button
              className={styles.modalClose}
              onClick={onCancel}
              aria-label="Cerrar"
            >
              ✕
            </button>
          </div>

          {/* Body */}
          <div className={styles.modalBody}>
            <p id="withdraw-description" className={styles.modalDescription}>
              Dejarás de permitir <strong>{consentLabel}</strong> a partir de ahora.
            </p>
            <div className={styles.consentDetails}>
              <p className={styles.detailsLabel}>Consentimiento otorgado:</p>
              <p className={styles.detailsValue}>{formatDate(consent.granted_at)}</p>
            </div>
          </div>

          {/* Footer */}
          <div className={styles.modalFooter}>
            <button
              className={styles.buttonCancel}
              onClick={onCancel}
              disabled={isWithdrawing}
            >
              Cancelar
            </button>
            <button
              className={styles.buttonConfirm}
              onClick={onConfirm}
              disabled={isWithdrawing}
              aria-busy={isWithdrawing}
            >
              {isWithdrawing ? (
                <>
                  <span className={styles.spinner} />
                  Revocando...
                </>
              ) : (
                'Revocar'
              )}
            </button>
          </div>

          {/* Legal notice */}
          <div className={styles.modalNotice}>
            <p className={styles.noticeText}>
              La revocación será efectiva inmediatamente. <br />
              <span className={styles.noticeSmall}>Art. 7.3 GDPR</span>
            </p>
          </div>
        </div>
      </div>
    </>
  );
};
