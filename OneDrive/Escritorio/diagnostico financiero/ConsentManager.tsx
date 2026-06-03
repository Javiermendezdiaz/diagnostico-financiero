import React, { useState } from 'react';
import { useDataRights } from '@/hooks/useDataRights';
import { ConsentRow } from './ConsentRow';
import { WithdrawConfirmationModal } from './WithdrawConfirmationModal';
import { ComplianceNotice } from './ComplianceNotice';
import styles from './ConsentManager.module.css';

/**
 * Consent Manager — GDPR Art. 7 compliance UI
 * Displays active consents and enables withdrawal
 */
export const ConsentManager: React.FC = () => {
  const { consents, loading, error, withdrawConsent } = useDataRights();
  const [selectedConsentId, setSelectedConsentId] = useState<string | null>(null);
  const [isWithdrawing, setIsWithdrawing] = useState(false);
  const [withdrawSuccess, setWithdrawSuccess] = useState(false);

  const handleWithdraw = async () => {
    if (!selectedConsentId) return;
    setIsWithdrawing(true);
    try {
      await withdrawConsent(selectedConsentId);
      setWithdrawSuccess(true);
      setTimeout(() => {
        setSelectedConsentId(null);
        setWithdrawSuccess(false);
      }, 2000);
    } catch (err) {
      console.error('Withdrawal failed:', err);
    } finally {
      setIsWithdrawing(false);
    }
  };

  const consentTypeLabels: Record<string, string> = {
    pdf_generation: 'Generación de PDFs',
    email_communication: 'Comunicación por email',
    analytics: 'Analítica y mejora',
    third_party: 'Compartir con terceros',
  };

  const selectedConsent = consents.find(c => c.id === selectedConsentId);

  return (
    <div className={styles.consentManager}>
      <div className={styles.header}>
        <h2>Tus consentimientos</h2>
        <p className={styles.subtitle}>Controla qué datos autorizas procesar</p>
      </div>

      {loading && (
        <div className={styles.spinner}>
          <div className={styles.spinnerInner} />
          <span>Cargando consentimientos...</span>
        </div>
      )}

      {error && (
        <div className={styles.errorBanner}>
          <span className={styles.errorIcon}>⚠️</span>
          <div>
            <p className={styles.errorTitle}>Error al cargar</p>
            <p className={styles.errorMessage}>{error}</p>
          </div>
        </div>
      )}

      {!loading && consents.length === 0 && (
        <div className={styles.empty}>
          <p>No tienes consentimientos activos</p>
        </div>
      )}

      {!loading && consents.length > 0 && (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Tipo de consentimiento</th>
                <th>Otorgado</th>
                <th>Expira</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {consents.map(consent => (
                <ConsentRow
                  key={consent.id}
                  consent={consent}
                  label={consentTypeLabels[consent.consent_type] || consent.consent_type}
                  isSelected={selectedConsentId === consent.id}
                  onWithdraw={() => setSelectedConsentId(consent.id)}
                  disabled={isWithdrawing}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <WithdrawConfirmationModal
        isOpen={selectedConsentId !== null && !withdrawSuccess}
        consent={selectedConsent}
        consentLabel={selectedConsent ? consentTypeLabels[selectedConsent.consent_type] || selectedConsent.consent_type : ''}
        isWithdrawing={isWithdrawing}
        onConfirm={handleWithdraw}
        onCancel={() => setSelectedConsentId(null)}
      />

      {withdrawSuccess && (
        <div className={styles.successBanner}>
          <span className={styles.successIcon}>✓</span>
          <p>Consentimiento retirado correctamente</p>
        </div>
      )}

      <ComplianceNotice />
    </div>
  );
};
