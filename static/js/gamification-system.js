/**
 * Gamification System for ESPEJO FANTASMA SPRINT 7
 * Implements points tracking, badge unlocks, progress visualization
 * Connects to backend API for persistent storage
 * A/B Testing: SUPREMO shows full gamification; CONTROL shows no badges/points
 */

const GamificationSystem = (() => {
  const STYLES = `
    .gamification-panel {
      background: white;
      border-radius: 12px;
      padding: 20px;
      margin: 20px 0;
      border-left: 4px solid #FDD731;
      font-family: 'Poppins', sans-serif;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .points-display {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
    }

    .points-counter {
      font-size: 32px;
      font-weight: 700;
      color: #FDD731;
    }

    .points-label {
      font-size: 12px;
      color: #343434;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .progress-ring-container {
      position: relative;
      width: 100px;
      height: 100px;
    }

    .progress-ring {
      transform: rotate(-90deg);
      transform-origin: 50% 50%;
    }

    .progress-ring-bg {
      fill: none;
      stroke: #FAF8F3;
      stroke-width: 6;
    }

    .progress-ring-fill {
      fill: none;
      stroke: #FDD731;
      stroke-width: 6;
      stroke-linecap: round;
      transition: stroke-dashoffset 0.5s ease;
    }

    .progress-percentage {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      font-size: 18px;
      font-weight: 700;
      color: #020203;
    }

    .badges-section {
      margin-top: 20px;
    }

    .badges-label {
      font-size: 12px;
      color: #343434;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 12px;
      display: block;
    }

    .badges-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(60px, 1fr));
      gap: 12px;
    }

    .badge {
      text-align: center;
      cursor: pointer;
      transition: transform 0.2s ease;
    }

    .badge:hover {
      transform: scale(1.1);
    }

    .badge-icon {
      font-size: 32px;
      margin-bottom: 4px;
    }

    .badge-name {
      font-size: 10px;
      color: #343434;
      font-weight: 600;
    }

    .badge.locked {
      opacity: 0.3;
      cursor: not-allowed;
    }

    .badge.locked:hover {
      transform: scale(1);
    }

    .badge.unlocked {
      animation: badge-unlock 0.6s ease;
    }

    @keyframes badge-unlock {
      0% {
        transform: scale(0);
        opacity: 0;
      }
      50% {
        transform: scale(1.2);
      }
      100% {
        transform: scale(1);
        opacity: 1;
      }
    }

    .streak-counter {
      display: inline-block;
      background: #FAF8F3;
      padding: 8px 16px;
      border-radius: 20px;
      font-size: 13px;
      color: #020203;
      font-weight: 600;
      margin-top: 12px;
    }

    .streak-flame {
      font-size: 16px;
      margin-right: 4px;
    }
  `;

  const BADGES = {
    starter: {
      id: "starter",
      name: "Novato",
      icon: "🎯",
      requiredPoints: 0,
      description: "Completa tu primer paso",
    },
    explorer: {
      id: "explorer",
      name: "Explorador",
      icon: "🗺️",
      requiredPoints: 25,
      description: "Completa 25 puntos",
    },
    master: {
      id: "master",
      name: "Maestro",
      icon: "🏆",
      requiredPoints: 100,
      description: "Acumula 100 puntos",
    },
    champion: {
      id: "champion",
      name: "Campeón",
      icon: "👑",
      requiredPoints: 250,
      description: "Alcanza 250 puntos",
    },
    sage: {
      id: "sage",
      name: "Sabio",
      icon: "🧙",
      requiredPoints: 500,
      description: "Llega a 500 puntos",
    },
  };

  function injectStyles() {
    if (document.querySelector("#gamification-styles")) return;
    const styleEl = document.createElement("style");
    styleEl.id = "gamification-styles";
    styleEl.textContent = STYLES;
    document.head.appendChild(styleEl);
  }

  async function fetchUserGamification(coupleId) {
    try {
      const response = await fetch(`/api/gamification/points/${coupleId}`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.warn("GamificationSystem: Could not fetch points", error);
    }

    return {
      couple_id: coupleId,
      points_total: 0,
      badges: [],
      streak_days: 0,
    };
  }

  function getBadgesUnlocked(totalPoints) {
    return Object.values(BADGES).filter((badge) => totalPoints >= badge.requiredPoints);
  }

  function createBadgesHTML(unlockedBadges) {
    let html = '<div class="badges-section"><label class="badges-label">🏅 Insignias</label><div class="badges-grid">';

    Object.values(BADGES).forEach((badge) => {
      const isUnlocked = unlockedBadges.some((b) => b.id === badge.id);
      html += `
        <div class="badge ${isUnlocked ? 'unlocked' : 'locked'}" title="${badge.description}">
          <div class="badge-icon">${badge.icon}</div>
          <div class="badge-name">${badge.name}</div>
        </div>
      `;
    });

    html += "</div></div>";
    return html;
  }

  function createProgressRing(percentage) {
    const radius = 45;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return `
      <div class="progress-ring-container">
        <svg class="progress-ring" width="100" height="100" viewBox="0 0 100 100">
          <circle class="progress-ring-bg" cx="50" cy="50" r="${radius}" />
          <circle
            class="progress-ring-fill"
            cx="50"
            cy="50"
            r="${radius}"
            style="stroke-dasharray: ${circumference}; stroke-dashoffset: ${strokeDashoffset};"
          />
        </svg>
        <div class="progress-percentage">${percentage}%</div>
      </div>
    `;
  }

  async function render(selector, coupleId) {
    injectStyles();

    const container = document.querySelector(selector);
    if (!container) {
      console.warn(`GamificationSystem: selector "${selector}" not found`);
      return;
    }

    const gamificationData = await fetchUserGamification(coupleId);
    const totalPoints = gamificationData.points_total || 0;
    const maxPoints = 500;
    const percentage = Math.min(100, Math.floor((totalPoints / maxPoints) * 100));
    const unlockedBadges = getBadgesUnlocked(totalPoints);
    const streakDays = gamificationData.streak_days || 0;

    let html = '<div class="gamification-panel">';

    // Points display
    html += `
      <div class="points-display">
        <div>
          <div class="points-counter">${totalPoints}</div>
          <div class="points-label">Puntos Acumulados</div>
        </div>
        ${createProgressRing(percentage)}
      </div>
    `;

    // Badges
    html += createBadgesHTML(unlockedBadges);

    // Streak counter
    if (streakDays > 0) {
      html += `
        <div class="streak-counter">
          <span class="streak-flame">🔥</span>
          ${streakDays} día${streakDays > 1 ? 's' : ''} en racha
        </div>
      `;
    }

    html += "</div>";
    container.innerHTML = html;
  }

  return {
    render: render,
    injectStyles: injectStyles,
    fetchUserGamification: fetchUserGamification,
  };
})();

// Auto-render if FEATURE_FLAGS indicate SUPREMO cohort
document.addEventListener("DOMContentLoaded", () => {
  if (window.FEATURE_FLAGS && window.FEATURE_FLAGS.features?.ux_gamification) {
    const coupleId = sessionStorage.getItem("couple_id") || "default-test";
    const container = document.querySelector("#gamification-container");
    if (container) {
      GamificationSystem.render("#gamification-container", coupleId);
    }
  }
});
