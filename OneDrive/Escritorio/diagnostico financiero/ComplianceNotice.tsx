import React from 'react';
import styles from './ConsentManager.module.css';

/**
 * GDPR Art. 7 compliance notice
 * Explains user's withdrawal rights
 */
export const ComplianceNotice: React.FC = () => {
  return (
    <div className={styles.complianceNotice}>
      <div className={styles.noticeIcon}>ℹ️</div>
      <div className={styles.noticeContent}>
        <p className={styles.noticeTitle}>Tus derechos</p>
        <p className={styles.noticeBody}>
          Puedes revocar cualquier consentimiento en cualquier momento sin que
          afecte a la licitud del tratamiento anterior. La revocación es tan
          sencilla como el otorgamiento.
        </p>
        <p className={styles.noticeArticle}>Art. 7(3) GDPR — Withdrawal of consent</p>
      </div>
    </div>
  );
};
