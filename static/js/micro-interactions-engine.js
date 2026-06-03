/**
 * Micro-Interactions Engine for ESPEJO FANTASMA SPRINT 7
 * Implements button ripple effects, input focus glow, success confetti
 * Enhances perceived responsiveness and joy factor
 * A/B Testing: SUPREMO shows full interactions; CONTROL shows minimal feedback
 */

const MicroInteractionsEngine = (() => {
  const STYLES = `
    @keyframes ripple {
      to {
        transform: scale(4);
        opacity: 0;
      }
    }

    .ripple {
      position: absolute;
      border-radius: 50%;
      background: rgba(253, 215, 49, 0.5);
      transform: scale(0);
      animation: ripple 0.6s ease-out;
      pointer-events: none;
    }

    @keyframes input-glow {
      0% {
        box-shadow: 0 0 0 0 rgba(253, 215, 49, 0.5);
      }
      70% {
        box-shadow: 0 0 0 10px rgba(253, 215, 49, 0);
      }
      100% {
        box-shadow: 0 0 0 0 rgba(253, 215, 49, 0);
      }
    }

    input:focus,
    textarea:focus {
      animation: input-glow 0.5s ease-out;
    }

    @keyframes success-bounce {
      0% {
        transform: scale(0) translateY(0);
        opacity: 1;
      }
      100% {
        transform: scale(1) translateY(-100px);
        opacity: 0;
      }
    }

    .confetti {
      position: fixed;
      pointer-events: none;
      font-size: 24px;
      animation: success-bounce 1s ease-out forwards;
    }

    @keyframes success-checkmark {
      0% {
        transform: scale(0) rotate(-45deg);
      }
      50% {
        transform: scale(1.2);
      }
      100% {
        transform: scale(1) rotate(0);
      }
    }

    .success-checkmark {
      display: inline-block;
      animation: success-checkmark 0.6s ease;
    }

    @keyframes button-press {
      0% {
        transform: translateY(0) scale(1);
      }
      50% {
        transform: translateY(2px) scale(0.98);
      }
      100% {
        transform: translateY(0) scale(1);
      }
    }

    button.micro-interaction {
      position: relative;
      overflow: hidden;
    }

    button.micro-interaction:active {
      animation: button-press 0.2s ease;
    }

    .input-success {
      border-color: #43d692;
      background-color: rgba(67, 214, 146, 0.05);
    }

    .input-error {
      border-color: #ff6b6b;
      background-color: rgba(255, 107, 107, 0.05);
    }
  `;

  const CONFETTI_EMOJIS = ["🎉", "⭐", "🎊", "✨", "🏆"];

  function injectStyles() {
    if (document.querySelector("#micro-interactions-styles")) return;
    const styleEl = document.createElement("style");
    styleEl.id = "micro-interactions-styles";
    styleEl.textContent = STYLES;
    document.head.appendChild(styleEl);
  }

  function addRippleEffect(element) {
    element.addEventListener("click", (e) => {
      const ripple = document.createElement("span");
      ripple.className = "ripple";

      const rect = element.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      ripple.style.width = ripple.style.height = size + "px";
      ripple.style.left = x + "px";
      ripple.style.top = y + "px";

      element.appendChild(ripple);

      setTimeout(() => ripple.remove(), 600);
    });
  }

  function showSuccessConfetti(centerElement) {
    const rect = centerElement.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    for (let i = 0; i < 12; i++) {
      const confetti = document.createElement("div");
      confetti.className = "confetti";
      confetti.textContent = CONFETTI_EMOJIS[Math.floor(Math.random() * CONFETTI_EMOJIS.length)];

      const angle = (Math.PI * 2 * i) / 12;
      const velocity = 3 + Math.random() * 3;
      const offsetX = Math.cos(angle) * velocity * 10;
      const offsetY = Math.sin(angle) * velocity * 10;

      confetti.style.left = centerX + offsetX + "px";
      confetti.style.top = centerY + offsetY + "px";

      document.body.appendChild(confetti);

      setTimeout(() => confetti.remove(), 1000);
    }
  }

  function addInputFeedback(inputElement) {
    inputElement.addEventListener("input", () => {
      if (inputElement.value.length > 0) {
        inputElement.classList.add("input-success");
        inputElement.classList.remove("input-error");
      } else {
        inputElement.classList.remove("input-success", "input-error");
      }
    });

    inputElement.addEventListener("invalid", () => {
      inputElement.classList.add("input-error");
      inputElement.classList.remove("input-success");
    });
  }

  function init() {
    injectStyles();

    // Add ripple to all buttons
    document.querySelectorAll("button").forEach((btn) => {
      btn.classList.add("micro-interaction");
      addRippleEffect(btn);
    });

    // Add feedback to all inputs
    document.querySelectorAll("input, textarea").forEach((input) => {
      addInputFeedback(input);
    });
  }

  return {
    init: init,
    injectStyles: injectStyles,
    addRippleEffect: addRippleEffect,
    showSuccessConfetti: showSuccessConfetti,
    addInputFeedback: addInputFeedback,
  };
})();

// Auto-initialize if FEATURE_FLAGS indicate SUPREMO cohort
document.addEventListener("DOMContentLoaded", () => {
  if (window.FEATURE_FLAGS && window.FEATURE_FLAGS.features?.ux_micro_interactions) {
    MicroInteractionsEngine.init();
  }
});
