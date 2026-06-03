import React from 'react';
import { ConsentRecord } from '@/hooks/useDataRights';
import styles from './ConsentManager.module.css';

interface ConsentRowProps {
  consent: ConsentRecord;
  label: string;
  isSelected: boolean;
  onWithdraw: () => void;
  disabled: boolean;
}

export const ConsentRow: React.FC<ConsentRowProps> = ({
  consent,
  label,
  isSelected,
  onWithdraw,
  disabled,
}) => {
  const formatDate = (date: string) => {
    return new Intl.DateTimeFormat('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(new Date(date));
  };

  const isWithdrawn = consent.is_withdrawn;
  const isExpired = new Date(consent.expires_at) < new Date();

  const getStatusBadge = () => {
    if (isWithdrawn) {
      return { label: 'Retirado', className: styles.statusRetracted };
    }
    if (isExpired) {
      return { label: 'Expirado', className: styles.statusExpired };
    }
    return { label: 'Activo', className: styles.statusActive };
  };

  const status = getStatusBadge();
  const canWithdraw = !isWithdrawn && !isExpired;

  return (
    <tr className={isSelected ? styles.rowSelected : ''}>
      <td className={styles.cellType}>{label}</td>
      <td className={styles.cellDate}>{formatDate(consent.granted_at)}</td>
      <td className={styles.cellDate}>{formatDate(consent.expires_at)}</td>
      <td>
        <span className={`${styles.badge} ${status.className}`}>
          {status.label}
        </span>
      </td>
      <td className={styles.cellActions}>
        {canWithdraw ? (
          <button
            className={styles.buttonWithdraw}
            onClick={onWithdraw}
            disabled={disabled}
            aria-label={`Revocar consentimiento para ${label}`}
          >
            Revocar
          </button>
        ) : (
          <span className={styles.actionDisabled}>—</span>
        )}
      </td>
    </tr>
  );
};
