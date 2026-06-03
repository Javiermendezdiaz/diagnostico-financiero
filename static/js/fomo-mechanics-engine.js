/**
 * FOMO Mechanics Engine for ESPEJO FANTASMA SPRINT 7
 * Implements exit-intent modal, real-time viewing counter
 * Psychological trigger: loss aversion + social proof combination
 * A/B Testing: SUPREMO shows FOMO mechanics; CONTROL shows nothing
 */

const FOMOMechanicsEngine = (() => {
  const STYLES = `
    .fomo-modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
      animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
      }
      to {
        opacity: 1;
      }
    }

    .fomo-modal {
      background: white;
      border-radius: 16px;
      padding: 40px;
      max-width: 400px;
      text-align: center;
      font-family: 'Poppins', sans-serif;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      animation: slideUp 0.4s ease;
      position: relative;
    }

    @keyframes slideUp {
      from {
        transform: translateY(60px);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }

    .fomo-close {
      position: absolute;
      top: 16px;
      right: 16px;
      background: none;
      border: none;
      font-size: 24px;
      cursor: pointer;
      color: #343434;
      padding: 0;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .fomo-close:hover {
      background: #FAF8F3;
      border-radius: 50%;
    }

    .fomo-title {
      font-size: 24px;
      font-weight: 700;
      color: #020203;
      margin-bottom: 12px;
    }

    .fomo-highlight {
      color: #FDD731;
    }

    .fomo-subtitle {
      font-size: 14px;
      color: #343434;
      margin-bottom: 24px;
      line-height: 1.5;
    }

    .fomo-offer {
      background: linear-gradient(135deg, #FDD731 0%, #F4CB2E 100%);
      padding: 16px 20px;
      border-radius: 12px;
      margin-bottom: 24px;
      font-weight: 700;
      color: #020203;
    }

    .fomo-cta {
      background: #020203;
      color: #FDD731;
      padding: 14px 32px;
      border: none;
      border-radius: 8px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      font-family: 'Poppins', sans-serif;
      margin-bottom: 12px;
      width: 100%;
      transition: all 0.2s ease;
    }

    .fomo-cta:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 20px rgba(2, 2, 3, 0.3);
    }

    .fomo-cta:active {
      transform: translateY(0);
    }

    .fomo-decline {
      background: transparent;
      color: #343434;
      padding: 12px;
      border: none;
      font-size: 13px;
      cursor: pointer;
      font-family: 'Poppins', sans-serif;
      text-decoration: underline;
    }

    .fomo-decline:hover {
      color: #020203;
    }

    .viewing-counter {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #FAF8F3;
      padding: 8px 16px;
      border-radius: 20px;
      font-size: 13px;
      color: #020203;
      font-weight: 600;
      margin: 20px 0;
    }

    .viewing-counter-icon {
      font-size: 16px;
      animation: pulse 1.5s ease-in-out infinite;
    }

    @keyframes pulse {
      0%, 100% {
        opacity: 1;
      }
      50% {
        opacity: 0.5;
      }
    }
  `;

  let isExitIntentTriggered = false;

  function injectStyles() {
    if (document.querySelector("#fomo-styles")) return;
    const styleEl = document.createElement("style");
    styleEl.id = "fomo-styles";
    styleEl.textContent = STYLES;
    document.head.appendChild(styleEl);
  }

  function showExitIntentModal() {
    if (isExitIntentTriggered) return;
    isExitIntentTriggered = true;

    const overlay = document.createElement("div");
    overlay.className = "fomo-modal-overlay";

    overlay.innerHTML = `
      <div class="fomo-modal">
        <button class="fomo-close" onclick="this.closest('.fomo-modal-overlay').remove()">✕</button>
        <h2 class="fomo-title">¡Espera un segundo!</h2>
        <p class="fomo-subtitle">
          No es demasiado tarde para obtener tu <span class="fomo-highlight">Diagnóstico Élite</span> con descuento especial
        </p>
        <div class="fomo-offer">
          🎯 20% OFF solo para hoy
        </div>
        <button class="fomo-cta" onclick="handleFomoAccept()">Sí, quiero el Diagnóstico</button>
        <button class="fomo-decline" onclick="this.closest('.fomo-modal-overlay').remove()">No, gracias</button>
      </div>
    `;

    document.body.appendChild(overlay);
  }

  function createViewingCounter(containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    let viewingCount = Math.floor(Math.random() * 20) + 5; // Random 5-25

    const counter = document.createElement("div");
    counter.className = "viewing-counter";
    counter.innerHTML = `<span class="viewing-counter-icon">👁️</span> ${viewingCount} personas viendo esto`;

    container.appendChild(counter);

    // Simulate real-time updates every 15-30 seconds
    setInterval(() => {
      if (Math.random() > 0.5) {
        viewingCount += 1;
      } else if (viewingCount > 0) {
        viewingCount -= 1;
      }
      counter.textContent = `👁️ ${viewingCount} personas viendo esto`;
    }, 15000 + Math.random() * 15000);
  }

  function initExitIntent() {
    document.addEventListener("mouseleave", (e) => {
      // Only trigger if mouse leaves from top of viewport (typical exit behavior)
      if (e.clientY <= 0) {
        showExitIntentModal();
      }
    });
  }

  function init(options = {}) {
    injectStyles();

    if (options.exitIntent !== false) {
      initExitIntent();
    }

    if (options.viewingCounterSelector) {
      createViewingCounter(options.viewingCounterSelector);
    }
  }

  return {
    init: init,
    injectStyles: injectStyles,
    showExitIntentModal: showExitIntentModal,
    createViewingCounter: createViewingCounter,
  };
})();

// Global handler for FOMO CTA acceptance
function handleFomoAccept() {
  const modal = document.querySelector(".fomo-modal-overlay");
  if (modal) modal.remove();

  // Trigger confetti celebration
  if (window.MicroInteractionsEngine) {
    const startBtn = document.querySelector("#startBtn");
    if (startBtn) {
      MicroInteractionsEngine.showSuccessConfetti(startBtn);
    }
  }

  // Scroll to main CTA
  const startBtn = document.querySelector("#startBtn");
  if (startBtn) {
    startBtn.scrollIntoView({ behavior: "smooth" });
    startBtn.focus();
  }
}

// Auto-initialize if FEATURE_FLAGS indicate SUPREMO cohort
document.addEventListener("DOMContentLoaded", () => {
  if (window.FEATURE_FLAGS && window.FEATURE_FLAGS.features?.ux_fomo_mechanics) {
    FOMOMechanicsEngine.init({
      exitIntent: true,
      viewingCounterSelector: "#viewing-counter-container",
    });
  }
});
