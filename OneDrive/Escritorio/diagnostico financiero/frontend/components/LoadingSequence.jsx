/**
 * LoadingSequence Component
 *
 * Pantalla de espera de 5.5 segundos que:
 * 1. Simula procesamiento de PDF
 * 2. Revela insights personalizados progresivamente
 * 3. Crea curiosidad + sensación de valor
 * 4. Transiciona a pantalla de créditos/pago
 *
 * Psicología:
 * - Loading animado hace que el usuario ESPERE (atención)
 * - Mensajes personalizados crean sentimiento de "AI analizó MIS datos"
 * - Página final con "nombre + páginas + problema específico" activa impulso de compra
 */

import React, { useState, useEffect } from 'react';
import { useSpring, animated, config } from '@react-spring/web';
import './LoadingSequence.css';

const LoadingSequence = ({ diagnosticId, userId, diagnosticData, onComplete }) => {
  const [stage, setStage] = useState('loading');      // 'loading' → 'complete'
  const [currentMessage, setCurrentMessage] = useState(0);
  const [blurAmount, setBlurAmount] = useState(20);

  // Messages progresivos (timestamps: 0ms, 1200ms, 2400ms, 3600ms, 4800ms)
  const messages = [
    {
      time: 0,
      text: diagnosticData?.debt_score > 50
        ? `Procesando Módulo de Deuda... Detectado nivel crítico en Sección 3`
        : `Procesando Módulo de Deuda... Evaluando estrategias de ahorro`
    },
    {
      time: 1200,
      text: `Cruzando datos de Patrimonio Neto (${diagnosticData?.liquidity_months?.toFixed(1)} meses de cobertura)`
    },
    {
      time: 2400,
      text: `Calculando Efecto Retrovisor... ${diagnosticData?.evaporated_percentage?.toFixed(1)}% de ingresos evaporados`
    },
    {
      time: 3600,
      text: `Diseñando tu Plan de Acción a 90 días basado en tu perfil`
    },
    {
      time: 4800,
      text: `Finalizando maquetación del informe de 38 páginas...`
    }
  ];

  // Animate blur effect (loop during loading)
  useEffect(() => {
    const blurInterval = setInterval(() => {
      setBlurAmount(prev => {
        if (prev === 20) return 0;
        if (prev === 0) return 15;
        return prev;
      });
    }, 300);
    return () => clearInterval(blurInterval);
  }, []);

  // Message progression (0ms → 5500ms)
  useEffect(() => {
    const messageTimeouts = messages.map((msg, index) => {
      return setTimeout(() => {
        setCurrentMessage(index);
      }, msg.time);
    });

    // Finalizar loading a los 5500ms
    const completeTimeout = setTimeout(() => {
      setStage('complete');
    }, 5500);

    return () => {
      messageTimeouts.forEach(t => clearTimeout(t));
      clearTimeout(completeTimeout);
    };
  }, []);

  // Transición a pantalla final
  const fadeInComplete = useSpring({
    opacity: stage === 'complete' ? 1 : 0,
    transform: stage === 'complete' ? 'translateY(0px)' : 'translateY(20px)',
    config: config.slow
  });

  return (
    <div className="loading-sequence-container">
      {/* Loading phase (0-5.5s) */}
      {stage === 'loading' && (
        <div className="loading-phase">
          <div className="loading-content">
            {/* Page flip animation */}
            <div className="page-flip-container">
              <div
                className="page-flip"
                style={{
                  filter: `blur(${blurAmount}px)`,
                  transition: 'filter 300ms ease-in-out'
                }}
              >
                <div className="page-flip-left" />
                <div className="page-flip-right" />
              </div>
            </div>

            {/* Messages */}
            <div className="messages">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`message ${index === currentMessage ? 'active' : 'inactive'}`}
                >
                  <p>{msg.text}</p>
                </div>
              ))}
            </div>

            {/* Progress bar */}
            <div className="progress-bar-container">
              <div
                className="progress-bar-fill"
                style={{
                  animation: `fillProgress 5500ms linear forwards`
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Complete phase (5.5s+) */}
      {stage === 'complete' && (
        <animated.div
          className="complete-phase"
          style={fadeInComplete}
        >
          <div className="complete-content">
            {/* Portada simulada */}
            <div className="simulated-cover">
              <div className="cover-header">
                <h1>Auditoría Estratégica</h1>
                <p className="user-name">{diagnosticData?.user_name || 'Tu nombre'}</p>
              </div>

              <div className="cover-metrics">
                {/* Métrica principal: dinero evaporado anualmente */}
                <div className="metric-box">
                  <p className="metric-label">Dinero que se evapora anualmente</p>
                  <p className="metric-value">
                    €{(diagnosticData?.evaporated_amount / 10).toFixed(0)}
                  </p>
                  <p className="metric-unit">/año</p>
                </div>

                {/* Health score */}
                <div className="metric-box">
                  <p className="metric-label">Salud Financiera</p>
                  <p className="metric-value">{diagnosticData?.health_score?.toFixed(0)}%</p>
                </div>

                {/* Pages count */}
                <div className="metric-box">
                  <p className="metric-label">Informe</p>
                  <p className="metric-value">38</p>
                  <p className="metric-unit">páginas</p>
                </div>
              </div>

              <div className="cover-footer">
                <p className="tagline">
                  Tu análisis personalizado está listo. Hemos identificado el punto exacto
                  donde puedes mejorar tu patrimonio.
                </p>
              </div>
            </div>

            {/* Credit status */}
            <div className="credit-status-box">
              <p className="credit-label">Créditos disponibles</p>
              <div className="credit-display">
                <span className="available">{diagnosticData?.credits_available || 0}</span>
                <span className="slash">/</span>
                <span className="required">500</span>
              </div>
              <p className="credit-hint">
                {diagnosticData?.credits_available >= 500
                  ? '¡Tienes suficientes créditos para descargar tu PDF!'
                  : `Te faltan ${diagnosticData?.credits_needed_for_pdf || 0} créditos`}
              </p>
            </div>

            {/* CTA Button */}
            <button
              className={`cta-button ${
                diagnosticData?.credits_available >= 500 ? 'download' : 'purchase'
              }`}
              onClick={onComplete}
            >
              {diagnosticData?.credits_available >= 500 ? (
                <>
                  <span className="button-icon">📥</span>
                  <span className="button-text">Descargar mi Auditoría</span>
                </>
              ) : (
                <>
                  <span className="button-icon">💳</span>
                  <span className="button-text">
                    Agregar 300 créditos (29€)
                  </span>
                </>
              )}
            </button>

            {/* Fallback message */}
            {diagnosticData?.credits_available >= 500 && (
              <p className="accessibility-message">
                Pulsa para descargar tu informe personalizado en PDF
              </p>
            )}
          </div>
        </animated.div>
      )}

      <style jsx>{`
        @keyframes fillProgress {
          from { width: 0%; }
          to { width: 100%; }
        }
      `}</style>
    </div>
  );
};

export default LoadingSequence;
