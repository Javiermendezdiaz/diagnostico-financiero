<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="isOpen" class="modal-overlay" @click.self="handleCancel">
        <div class="modal-content glass-effect">
          <!-- Header -->
          <div class="modal-header">
            <h2 class="modal-title">Modo Espejo</h2>
            <button
              class="btn-close"
              @click="handleCancel"
              aria-label="Cerrar"
            >
              ✕
            </button>
          </div>

          <!-- Body -->
          <div class="modal-body">
            <div class="icon-container">
              <svg
                class="couple-icon"
                viewBox="0 0 200 200"
                xmlns="http://www.w3.org/2000/svg"
              >
                <!-- Left profile (user) -->
                <circle cx="60" cy="50" r="20" fill="#FDD731" opacity="0.8" />
                <path
                  d="M 40 80 Q 40 70 60 70 Q 80 70 80 80 L 80 120 Q 80 140 60 140 Q 40 140 40 120 Z"
                  fill="#FDD731"
                  opacity="0.6"
                />

                <!-- Right profile (partner) -->
                <circle cx="140" cy="50" r="20" fill="#020203" opacity="0.8" />
                <path
                  d="M 120 80 Q 120 70 140 70 Q 160 70 160 80 L 160 120 Q 160 140 140 140 Q 120 140 120 120 Z"
                  fill="#020203"
                  opacity="0.6"
                />

                <!-- Connection line -->
                <line
                  x1="80"
                  y1="100"
                  x2="120"
                  y2="100"
                  stroke="#FDD731"
                  stroke-width="2"
                  stroke-dasharray="4,4"
                />
              </svg>
            </div>

            <p class="modal-subtitle">
              Invita a tu pareja a responder las mismas preguntas de forma independiente
            </p>

            <div class="info-box">
              <h3>¿Cómo funciona?</h3>
              <ul class="info-list">
                <li>Tú respondes sin ver sus respuestas</li>
                <li>Ella responde sin ver las tuyas</li>
                <li>Recibís un análisis de alineación financiera</li>
              </ul>
            </div>
          </div>

          <!-- Footer -->
          <div class="modal-footer">
            <button
              class="btn btn-secondary"
              @click="handleCancel"
            >
              Saltarme
            </button>
            <button
              class="btn btn-primary"
              @click="handleInvite"
            >
              Sí, invitaré después
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  isOpen?: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'invite'): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const handleCancel = () => {
  emit('close')
}

const handleInvite = () => {
  emit('invite')
  emit('close')
}
</script>

<style scoped lang="scss">
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(2, 2, 3, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 90%;
  max-width: 420px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(253, 215, 49, 0.2);
  box-shadow: 0 8px 32px rgba(2, 2, 3, 0.15);
  overflow: hidden;
  animation: slideIn 0.3s ease-out;

  @media (max-width: 640px) {
    max-width: calc(100% - 24px);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid rgba(52, 52, 52, 0.1);
  background: linear-gradient(135deg, rgba(253, 215, 49, 0.05), rgba(32, 32, 32, 0.02));
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #020203;
  margin: 0;
  letter-spacing: 0.5px;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #343434;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;

  &:hover {
    color: #FDD731;
  }
}

.modal-body {
  padding: 32px 24px;
  text-align: center;
}

.icon-container {
  margin-bottom: 24px;
}

.couple-icon {
  width: 120px;
  height: 120px;
  margin: 0 auto;
  filter: drop-shadow(0 2px 8px rgba(2, 2, 3, 0.08));
}

.modal-subtitle {
  font-size: 14px;
  color: #343434;
  margin: 0 0 20px 0;
  line-height: 1.5;
  font-weight: 500;
}

.info-box {
  background: rgba(253, 215, 49, 0.06);
  border-left: 3px solid #FDD731;
  padding: 16px;
  border-radius: 8px;
  text-align: left;
  margin-bottom: 24px;

  h3 {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    color: #FDD731;
    margin: 0 0 12px 0;
    letter-spacing: 1px;
  }
}

.info-list {
  list-style: none;
  padding: 0;
  margin: 0;

  li {
    font-size: 13px;
    color: #020203;
    margin-bottom: 8px;
    position: relative;
    padding-left: 20px;
    line-height: 1.4;

    &::before {
      content: '→';
      position: absolute;
      left: 0;
      color: #FDD731;
      font-weight: bold;
    }

    &:last-child {
      margin-bottom: 0;
    }
  }
}

.modal-footer {
  display: flex;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid rgba(52, 52, 52, 0.1);
  background: rgba(250, 248, 243, 0.5);
}

.btn {
  flex: 1;
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.3px;
  text-transform: uppercase;

  &:hover {
    transform: translateY(-2px);
  }

  &:active {
    transform: translateY(0);
  }
}

.btn-primary {
  background: linear-gradient(135deg, #FDD731, #F4CB2E);
  color: #020203;
  box-shadow: 0 4px 12px rgba(253, 215, 49, 0.3);

  &:hover {
    box-shadow: 0 6px 16px rgba(253, 215, 49, 0.4);
  }
}

.btn-secondary {
  background: rgba(52, 52, 52, 0.1);
  color: #343434;
  border: 1px solid rgba(52, 52, 52, 0.2);

  &:hover {
    background: rgba(52, 52, 52, 0.15);
  }
}

.glass-effect {
  backdrop-filter: blur(10px);
}

/* Animations */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
