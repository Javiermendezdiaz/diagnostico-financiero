/**
 * ConfirmationModal — Fase 3 Enhanced UX
 * Reutilizable modal para confirmar acciones sensibles (especialmente Art. 17 deletion)
 *
 * Props:
 * - isOpen: boolean — Mostrar/ocultar modal
 * - title: string — Título del modal
 * - message: string — Mensaje principal
 * - confirmText: string — Texto del botón confirmar (default: "Continuar")
 * - cancelText: string — Texto del botón cancelar (default: "Cancelar")
 * - variant: "danger" | "warning" | "info" — Estilo (default: "info")
 * - onConfirm: () => void — Callback al confirmar
 * - onCancel: () => void — Callback al cancelar
 * - isLoading: boolean — Mostrar loading en botón confirmar
 * - disabled: boolean — Deshabilitar botones
 */

import React, { useEffect } from 'react';
import styles from './ConfirmationModal.module.css';

export interface ConfirmationModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  title,
  message,
  confirmText = 'Continuar',
  cancelText = 'Cancelar',
  variant = 'info',
  onConfirm,
  onCancel,
  isLoading = false,
  disabled = false,
}) => {
  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className={styles.backdrop}
        onClick={onCancel}
        role="presentation"
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className={styles.modal}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby="modal-message"
      >
        <div className={`${styles.content} ${styles[variant]}`}>
          {/* Icon by variant */}
          <div className={styles.iconContainer}>
            {variant === 'danger' && (
              <svg className={styles.icon} viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
              </svg>
            )}
            {variant === 'warning' && (
              <svg className={styles.icon} viewBox="0 0 24 24" fill="currentColor">
                <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
              </svg>
            )}
            {variant === 'info' && (
              <svg className={styles.icon} viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
              </svg>
            )}
          </div>

          {/* Title */}
          <h2 id="modal-title" className={styles.title}>
            {title}
          </h2>

          {/* Message */}
          <p id="modal-message" className={styles.message}>
            {message}
          </p>

          {/* Buttons */}
          <div className={styles.actions}>
            <button
              className={styles.cancelButton}
              onClick={onCancel}
              disabled={disabled || isLoading}
              aria-label={cancelText}
            >
              {cancelText}
            </button>
            <button
              className={`${styles.confirmButton} ${styles[variant]}`}
              onClick={onConfirm}
              disabled={disabled || isLoading}
              aria-label={confirmText}
            >
              {isLoading ? (
                <>
                  <span className={styles.spinner} aria-hidden="true" />
                  Procesando...
                </>
              ) : (
                confirmText
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
