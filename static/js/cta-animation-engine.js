/**
 * CTA Animation Engine for ESPEJO FANTASMA SPRINT 7
 * Implements pulsing, glowing, and countdown animations on CTAs.
 * A/B Testing: SUPREMO cohort shows full animations; CONTROL shows static.
 */

const CTAAnimationEngine = (() => {
  // CSS animations injected into <head>
  const STYLES = `
    @keyframes pulse-glow {
      0%, 100% {
        box-shadow: 0 0 0 0 rgba(253, 215, 49, 0.7);
      }
      50% {
        box-shadow: 0 0 0 20px rgba(253, 215, 49, 0);
      }
    }

    @keyframes soft-glow {
      0%, 100% {
        box-shadow: 0 4px 15px rgba(253, 215, 49, 0.4);
      }
      50% {
        box-shadow: 0 4px 25px rgba(253, 215, 49, 0.8);
      }
    }

    @keyframes pulse-scale {
      0%, 100% {
        transform: scale(1);
      }
      50% {
        transform: scale(1.05);
      }
    }

    .cta-pulse {
      animation: pulse-glow 2s infinite;
    }

    .cta-glow {
      animation: soft-glow 2s ease-in-out infinite;
    }

    .cta-scale {
      animation: pulse-scale 1.5s ease-in-out infinite;
    }

    .countdown-badge {
      display: inline-block;
      background-color: #FDD731;
      color: #020203;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      margin-left: 8px;
      font-family: 'Poppins', sans-serif;
    }

    .countdown-warning {
      background-color: #ff6b6b;
      color: white;
    }
  `;

  function injectStyles() {
    if (document.querySelector("#cta-animation-styles")) return;
    const styleEl = document.createElement("style");
    styleEl.id = "cta-animation-styles";
    styleEl.textContent = STYLES;
    document.head.appendChild(styleEl);
  }

  function addPulseAnimation(selector, options = {}) {
    const element = document.querySelector(selector);
    if (!element) {
      console.warn(`CTAAnimationEngine: selector "${selector}" not found`);
      return;
    }

    const animationType = options.animation || "pulse";
    element.classList.add(`cta-${animationType}`);
  }

  function addCountdownBadge(selector, durationSeconds = 86400, onExpire = null) {
    const element = document.querySelector(selector);
    if (!element) {
      console.warn(`CTAAnimationEngine: selector "${selector}" not found`);
      return;
    }

    const expiryTime = Date.now() + durationSeconds * 1000;

    function updateCountdown() {
      const now = Date.now();
      const remaining = expiryTime - now;

      if (remaining <= 0) {
        const badge = element.querySelector(".countdown-badge");
        if (badge) badge.remove();
        if (onExpire) onExpire();
        return;
      }

      const hours = Math.floor(remaining / (1000 * 60 * 60));
      const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));

      let badge = element.querySelector(".countdown-badge");
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "countdown-badge";
        element.appendChild(badge);
      }

      if (hours < 1) {
        badge.classList.add("countdown-warning");
        badge.textContent = `${minutes}m remaining`;
      } else {
        badge.classList.remove("countdown-warning");
        badge.textContent = `Expires in ${hours}h`;
      }
    }

    updateCountdown();
    setInterval(updateCountdown, 60000); // Update every minute
  }

  function addHoverEffect(selector) {
    const element = document.querySelector(selector);
    if (!element) {
      console.warn(`CTAAnimationEngine: selector "${selector}" not found`);
      return;
    }

    element.addEventListener("mouseenter", () => {
      element.style.transform = "translateY(-2px)";
      element.style.transition = "all 0.2s ease";
    });

    element.addEventListener("mouseleave", () => {
      element.style.transform = "translateY(0)";
    });
  }

  function init(selector, options = {}) {
    injectStyles();
    addPulseAnimation(selector, options);
    if (options.countdown) {
      addCountdownBadge(selector, options.countdownDuration, options.onExpire);
    }
    if (options.hoverEffect) {
      addHoverEffect(selector);
    }
  }

  return {
    init: init,
    injectStyles: injectStyles,
    addPulseAnimation: addPulseAnimation,
    addCountdownBadge: addCountdownBadge,
    addHoverEffect: addHoverEffect,
  };
})();

// Auto-initialize if FEATURE_FLAGS indicate SUPREMO cohort
document.addEventListener("DOMContentLoaded", () => {
  if (window.FEATURE_FLAGS && window.FEATURE_FLAGS.features?.ux_cta_animations) {
    // Apply to main CTA buttons
    CTAAnimationEngine.init("#startBtn", {
      animation: "pulse",
      hoverEffect: true,
    });

    // Apply to payment button with countdown
    CTAAnimationEngine.init("#paymentBtn", {
      animation: "glow",
      countdown: true,
      countdownDuration: 86400, // 24 hours
      hoverEffect: true,
    });
  }
});
