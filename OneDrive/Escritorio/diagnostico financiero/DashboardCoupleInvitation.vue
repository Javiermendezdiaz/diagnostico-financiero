<template>
  <div class="couple-invitation-card">
    <!-- Card Header -->
    <div class="card-header">
      <div class="header-content">
        <h3 class="card-title">Modo Espejo: Invita a tu Pareja</h3>
        <p class="card-subtitle">Análisis conjunto de alineación financiera</p>
      </div>
      <div class="header-icon">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2c5.5 0 10 4.5 10 10s-4.5 10-10 10S2 17.5 2 12 6.5 2 12 2m0 2c-4.4 0-8 3.6-8 8s3.6 8 8 8 8-3.6 8-8-3.6-8-8-8m0 1c3.9 0 7 3.1 7 7s-3.1 7-7 7-7-3.1-7-7 3.1-7 7-7m-2.5 3c-.8 0-1.5.7-1.5 1.5S8.7 11 9.5 11s1.5-.7 1.5-1.5S10.3 8 9.5 8m5 0c-.8 0-1.5.7-1.5 1.5s.7 1.5 1.5 1.5 1.5-.7 1.5-1.5-.7-1.5-1.5-1.5m-2.5 5c-1.1 0-2 .9-2 2h4c0-1.1-.9-2-2-2z"/>
        </svg>
      </div>
    </div>

    <!-- Card Content -->
    <div class="card-content">
      <!-- Status Display -->
      <div v-if="sessionStatus" class="status-section">
        <div class="status-badge" :class="`status-${sessionStatus}`">
          <span class="status-icon">{{ statusIcon }}</span>
          <span class="status-text">{{ statusLabel }}</span>
        </div>
      </div>

      <!-- Invitation Form (Initial State) -->
      <form v-if="!invitationSent" @submit.prevent="sendInvitation" class="invitation-form">
        <div class="form-group">
          <label for="partner-email" class="form-label">Email de tu pareja</label>
          <input
            id="partner-email"
            v-model="partnerEmail"
            type="email"
            class="form-input"
            placeholder="pareja@example.com"
            required
            :disabled="isLoading"
          />
          <p class="form-hint">Enviaremos un link para que responda las preguntas</p>
        </div>

        <button
          type="submit"
          class="btn btn-primary btn-full"
          :disabled="isLoading || !partnerEmail.trim()"
          :class="{ 'is-loading': isLoading }"
        >
          <span v-if="!isLoading">Enviar Invitación</span>
          <span v-else>Enviando...</span>
        </button>

        <p class="form-legal">
          Responderá con privacidad total. Los datos son simétricos.
        </p>
      </form>

      <!-- Confirmation State -->
      <div v-else class="confirmation-section">
        <div class="success-icon">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2m-2 15l-5-5 1.4-1.4L10 14.2l7.6-7.6L19 8l-9 9z" fill="#FDD731"/>
          </svg>
        </div>
        <h4 class="confirmation-title">Invitación Enviada</h4>
        <p class="confirmation-text">
          {{ partnerEmail }} recibirá un email con el link para responder
        </p>

        <div class="invite-link-section">
          <p class="invite-link-label">O comparte este link directamente:</p>
          <div class="invite-link-box">
            <input
              type="text"
              :value="inviteLink"
              readonly
              class="invite-link-input"
            />
            <button
              @click="copyInviteLink"
              class="btn-copy"
              :class="{ 'copied': linkCopied }"
            >
              {{ linkCopied ? '✓ Copiado' : 'Copiar' }}
            </button>
          </div>
        </div>

        <button
          @click="resetForm"
          class="btn btn-secondary btn-full"
        >
          Invitar a otro contacto
        </button>
      </div>
    </div>

    <!-- Card Footer Info -->
    <div class="card-footer">
      <div class="footer-item">
        <span class="footer-icon">🔒</span>
        <span class="footer-text">Datos privados y anónimos</span>
      </div>
      <div class="footer-item">
        <span class="footer-icon">⏱</span>
        <span class="footer-text">Link válido por 48 horas</span>
      </div>
      <div class="footer-item">
        <span class="footer-icon">📊</span>
        <span class="footer-text">Análisis automático al completar</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  coupleSessionId?: string
  initialStatus?: 'pending' | 'invited' | 'accepted' | 'in_progress' | 'completed'
}

defineProps<Props>()

const partnerEmail = ref('')
const invitationSent = ref(false)
const isLoading = ref(false)
const linkCopied = ref(false)
const inviteLink = ref('')
const sessionStatus = ref('')

const statusConfig = {
  pending: { icon: '⏳', label: 'Esperando invitación' },
  invited: { icon: '📧', label: 'Invitación enviada' },
  accepted: { icon: '✓', label: 'Pareja aceptó' },
  in_progress: { icon: '📋', label: 'Respondiendo preguntas' },
  completed: { icon: '✨', label: 'Análisis completado' },
}

const statusIcon = computed(() => {
  return statusConfig[sessionStatus.value as keyof typeof statusConfig]?.icon || '○'
})

const statusLabel = computed(() => {
  return statusConfig[sessionStatus.value as keyof typeof statusConfig]?.label || 'Sin estado'
})

const sendInvitation = async () => {
  if (!partnerEmail.value.trim()) return

  isLoading.value = true

  try {
    // Call backend endpoint
    const response = await fetch('/api/couple-mirror/invite', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        couple_session_id: props.coupleSessionId,
        partner_email: partnerEmail.value,
      }),
    })

    if (response.ok) {
      const data = await response.json()
      inviteLink.value = data.invite_url || `${window.location.origin}/couple-mirror/accept/${data.invite_token}`
      invitationSent.value = true
      sessionStatus.value = 'invited'
    } else {
      alert('Error enviando invitación. Intenta de nuevo.')
    }
  } catch (error) {
    console.error('Error:', error)
    alert('Error al enviar invitación.')
  } finally {
    isLoading.value = false
  }
}

const copyInviteLink = () => {
  navigator.clipboard.writeText(inviteLink.value)
  linkCopied.value = true
  setTimeout(() => {
    linkCopied.value = false
  }, 2000)
}

const resetForm = () => {
  partnerEmail.value = ''
  invitationSent.value = false
  linkCopied.value = false
  inviteLink.value = ''
}

// Initialize status from props
if (props.initialStatus) {
  sessionStatus.value = props.initialStatus
}
</script>

<style scoped lang="scss">
.couple-invitation-card {
  background: white;
  border-radius: 12px;
  border: 1px solid rgba(52, 52, 52, 0.1);
  box-shadow: 0 2px 8px rgba(2, 2, 3, 0.06);
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px;
  border-bottom: 1px solid rgba(52, 52, 52, 0.08);
  background: linear-gradient(135deg, rgba(253, 215, 49, 0.04), rgba(32, 32, 32, 0.01));
}

.header-content {
  flex: 1;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #020203;
  margin: 0 0 4px 0;
  letter-spacing: 0.3px;
}

.card-subtitle {
  font-size: 12px;
  color: #343434;
  margin: 0;
  font-weight: 400;
}

.header-icon {
  flex-shrink: 0;
  margin-left: 16px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(253, 215, 49, 0.1);
  border-radius: 8px;

  svg {
    width: 20px;
    height: 20px;
    fill: #FDD731;
  }
}

.card-content {
  padding: 24px;
}

.status-section {
  margin-bottom: 20px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;

  &.status-pending {
    background: rgba(255, 193, 7, 0.1);
    color: #f57f17;
  }

  &.status-invited {
    background: rgba(66, 165, 245, 0.1);
    color: #1976d2;
  }

  &.status-accepted {
    background: rgba(76, 175, 80, 0.1);
    color: #388e3c;
  }

  &.status-in_progress {
    background: rgba(156, 39, 176, 0.1);
    color: #6a1b9a;
  }

  &.status-completed {
    background: rgba(76, 175, 80, 0.1);
    color: #2e7d32;
  }
}

.status-icon {
  font-size: 14px;
}

.invitation-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: #020203;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.form-input {
  padding: 12px 12px;
  border: 1px solid rgba(52, 52, 52, 0.2);
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
  transition: all 0.2s;

  &:focus {
    outline: none;
    border-color: #FDD731;
    box-shadow: 0 0 0 3px rgba(253, 215, 49, 0.1);
  }

  &:disabled {
    background: rgba(52, 52, 52, 0.05);
    cursor: not-allowed;
  }
}

.form-hint {
  font-size: 12px;
  color: #343434;
  margin: 0;
  font-weight: 400;
}

.form-legal {
  font-size: 11px;
  color: #343434;
  text-align: center;
  margin: 8px 0 0 0;
  opacity: 0.7;
}

.btn {
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.3px;
  text-transform: uppercase;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &.is-loading {
    opacity: 0.8;
  }
}

.btn-primary {
  background: linear-gradient(135deg, #FDD731, #F4CB2E);
  color: #020203;
  box-shadow: 0 2px 8px rgba(253, 215, 49, 0.2);

  &:hover:not(:disabled) {
    box-shadow: 0 4px 12px rgba(253, 215, 49, 0.3);
  }
}

.btn-secondary {
  background: rgba(52, 52, 52, 0.1);
  color: #343434;
  border: 1px solid rgba(52, 52, 52, 0.2);

  &:hover:not(:disabled) {
    background: rgba(52, 52, 52, 0.15);
  }
}

.btn-full {
  width: 100%;
}

.confirmation-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 16px;
}

.success-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(253, 215, 49, 0.15);
  border-radius: 12px;

  svg {
    width: 32px;
    height: 32px;
  }
}

.confirmation-title {
  font-size: 16px;
  font-weight: 600;
  color: #020203;
  margin: 0;
}

.confirmation-text {
  font-size: 13px;
  color: #343434;
  margin: 0;
  line-height: 1.5;
}

.invite-link-section {
  width: 100%;
  padding: 16px;
  background: rgba(253, 215, 49, 0.04);
  border: 1px solid rgba(253, 215, 49, 0.2);
  border-radius: 8px;
}

.invite-link-label {
  font-size: 12px;
  color: #343434;
  margin: 0 0 12px 0;
  font-weight: 500;
}

.invite-link-box {
  display: flex;
  gap: 8px;
}

.invite-link-input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid rgba(52, 52, 52, 0.2);
  border-radius: 6px;
  font-size: 11px;
  font-family: 'Courier New', monospace;
  word-break: break-all;
  background: white;
  color: #020203;

  &:focus {
    outline: none;
    border-color: #FDD731;
  }
}

.btn-copy {
  padding: 8px 12px;
  background: #FDD731;
  color: #020203;
  border: none;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;

  &:hover {
    background: #F4CB2E;
  }

  &.copied {
    background: #4caf50;
    color: white;
  }
}

.card-footer {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid rgba(52, 52, 52, 0.08);
  background: rgba(250, 248, 243, 0.5);
  font-size: 12px;

  @media (max-width: 640px) {
    flex-direction: column;
    gap: 8px;
  }
}

.footer-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #343434;
  flex: 1;

  @media (max-width: 640px) {
    flex: auto;
  }
}

.footer-icon {
  font-size: 14px;
}

.footer-text {
  font-weight: 500;
}
</style>
