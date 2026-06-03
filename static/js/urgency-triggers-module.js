/**
 * Urgency Triggers Module for ESPEJO FANTASMA SPRINT 7
 * Implements countdown timer + scarcity messaging
 * Updates via WebSocket for real-time spot availability
 * A/B Testing: SUPREMO shows countdown + flash updates; CONTROL shows static text
 */

const UrgencyTriggersModule = (() => {
  const STYLES = `
    .urgency-banner {
      background: linear-gradient(135deg, #FDD731 0%, #F4CB2E 100%);
      padding: 16px 20px;
      border-radius: 8px;
      margin: 20px 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-family: 'Poppins', sans-serif;
      color: #020203;
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(253, 215, 49, 0.3);
      animation: slideDown 0.4s ease;
    }

    @keyframes slideDown {
      from {
        opacity: 0;
        transform: translateY(-20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .urgency-message {
      font-size: 16px;
      flex-grow: 1;
    }

    .urgency-timer {
      background: rgba(2, 2, 3, 0.2);
      padding: 8px 16px;
      border-radius: 20px;
      font-size: 14px;
      font-weight: 700;
      margin-left: 16px;
      white-space: nowrap;
      font-family: 'Courier New', monospace;
      animation: pulse-glow 2s ease-in-out infinite;
    }

    @keyframes pulse-glow {
      0%, 100% {
        box-shadow: 0 0 0 0 rgba(2, 2, 3, 0.3);
      }
      50% {
        box-shadow: 0 0 0 6px rgba(2, 2, 3, 0);
      }
    }

    .urgency-banner.critical {
      background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
      animation: flash-critical 1s ease-in-out infinite;
    }

    @keyframes flash-critical {
      0%, 100% {
        opacity: 1;
      }
      50% {
        opacity: 0.8;
      }
    }

    .urgency-banner.critical .urgency-timer {
      background: rgba(255, 255, 255, 0.3);
      color: white;
    }

    .scarcity-text {
      font-size: 13px;
      opacity: 0.9;
      margin-top: 8px;
    }

    .spots-indicator {
      display: inline-block;
      background: rgba(2, 2, 3, 0.2);
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 700;
      margin-left: 8px;
    }
  `;

  function injectStyles() {
    if (document.querySelector("#urgency-styles")) return;
    const styleEl = document.createElement("style");
    styleEl.id = "urgency-styles";
    styleEl.textContent = STYLES;
    document.head.appendChild(styleEl);
  }

  function createCountdownDisplay(remainingSeconds) {
    const hours = Math.floor(remainingSeconds / 3600);
    const minutes = Math.floor((remainingSeconds % 3600) / 60);
    const seconds = remainingSeconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s left`;
    }
  }

  function init(selector, options = {}) {
    injectStyles();

    const container = document.querySelector(selector);
    if (!container) {
      console.warn(`UrgencyTriggersModule: selector "${selector}" not found`);
      return;
    }

    const countdownDuration = options.countdownDuration || 86400; // 24 hours
    const updateInterval = options.updateInterval || 60000; // 1 minute
    const expiryTime = Date.now() + countdownDuration * 1000;

    // Initial render
    updateCountdown();

    // Update countdown every second
    const timerInterval = setInterval(updateCountdown, 1000);

    // Optional: fetch remaining spots from API
    if (options.apiEndpoint) {
      fetchAndUpdateSpots();
      setInterval(fetchAndUpdateSpots, updateInterval);
    }

    function updateCountdown() {
      const now = Date.now();
      const remaining = expiryTime - now;

      if (remaining <= 0) {
        clearInterval(timerInterval);
        container.innerHTML = '<div class="urgency-banner"><p class="urgency-message">⏰ Esta oferta ha expirado</p></div>';
        if (options.onExpire) options.onExpire();
        return;
      }

      const remainingSeconds = Math.floor(remaining / 1000);
      const countdownText = createCountdownDisplay(remainingSeconds);

      let html = '<div class="urgency-banner ';

      // Critical state: less than 1 hour
      if (remainingSeconds < 3600) {
        html += 'critical';
      }

      html += `">
        <div class="urgency-message">
          ⚡ Diagnóstico a Precio Especial
          <span class="spots-indicator">Últimas plazas</span>
        </div>
        <div class="urgency-timer">${countdownText}</div>
      </div>`;

      container.innerHTML = html;
    }

    async function fetchAndUpdateSpots() {
      try {
        const response = await fetch(options.apiEndpoint);
        if (response.ok) {
          const data = await response.json();
          // Update spots display if needed
          const spotsElement = container.querySelector(".spots-indicator");
          if (spotsElement && data.remaining_spots !== undefined) {
            if (data.remaining_spots <= 0) {
              spotsElement.textContent = "Sin plazas";
              spotsElement.style.background = "rgba(255, 107, 107, 0.3)";
            } else {
              spotsElement.textContent = `${data.remaining_spots} ${data.remaining_spots === 1 ? 'plaza' : 'plazas'}`;
            }
          }
        }
      } catch (error) {
        console.warn("UrgencyTriggersModule: Could not fetch spots", error);
      }
    }
  }

  return {
    init: init,
    injectStyles: injectStyles,
  };
})();

// Auto-initialize if FEATURE_FLAGS indicate SUPREMO cohort
document.addEventListener("DOMContentLoaded", () => {
  if (window.FEATURE_FLAGS && window.FEATURE_FLAGS.features?.ux_urgency_triggers) {
    const container = document.querySelector("#urgency-banner");
    if (container) {
      UrgencyTriggersModule.init("#urgency-banner", {
        countdownDuration: 86400, // 24 hours
        updateInterval: 60000, // 1 minute
        apiEndpoint: "/api/urgency-metrics",
      });
    }
  }
});
