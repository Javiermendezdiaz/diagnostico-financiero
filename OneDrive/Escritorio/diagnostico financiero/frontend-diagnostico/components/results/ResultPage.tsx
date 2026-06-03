'use client';

import { motion } from 'framer-motion';
import { useEffect } from 'react';
import confetti from 'canvas-confetti';

interface ResultPageProps {
  pdfUrl: string;
  onStartOver: () => void;
}

export const ResultPage = ({ pdfUrl, onStartOver }: ResultPageProps) => {
  useEffect(() => {
    // Trigger confetti on mount
    confetti({
      particleCount: 150,
      spread: 90,
      origin: { y: 0.6 },
    });
  }, []);

  const downloadPdf = () => {
    const link = document.createElement('a');
    link.href = pdfUrl;
    link.download = 'diagnostico-financiero.pdf';
    link.click();
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="text-center space-y-8"
    >
      {/* Success Animation */}
      <motion.div
        animate={{ rotate: [0, 360] }}
        transition={{ duration: 0.8, delay: 0.2 }}
        className="mx-auto w-32 h-32 bg-yellow-400 rounded-full flex items-center justify-center"
      >
        <motion.div
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 0.8, repeat: Infinity }}
          className="text-6xl"
        >
          ✅
        </motion.div>
      </motion.div>

      {/* Heading */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} delay={0.4}>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">¡Diagnóstico completado!</h1>
        <p className="text-lg text-gray-600">Tu informe personalizado está listo</p>
      </motion.div>

      {/* Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="bg-white rounded-lg p-8 shadow-sm border border-gray-100"
      >
        <div className="space-y-6">
          <div className="text-left">
            <h3 className="text-sm font-semibold text-gray-600 mb-3">Tu informe incluye:</h3>
            <ul className="space-y-3">
              <li className="flex items-start gap-3">
                <span className="text-2xl">📊</span>
                <span className="text-gray-700">
                  <strong>Diagnóstico</strong> — Tu situación financiera en números
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-2xl">🧠</span>
                <span className="text-gray-700">
                  <strong>Psicología</strong> — Creencias y patrones limitantes
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-2xl">⚠️</span>
                <span className="text-gray-700">
                  <strong>Stress Tests</strong> — Escenarios críticos y cobertura de emergencia
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-2xl">🎯</span>
                <span className="text-gray-700">
                  <strong>Plan 90 Días</strong> — Pasos concretos para transformar tu vida
                </span>
              </li>
            </ul>
          </div>
        </div>
      </motion.div>

      {/* CTA Buttons */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="space-y-3"
      >
        {/* Download PDF */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={downloadPdf}
          className="w-full bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-bold py-4 rounded-lg transition-all shadow-lg"
        >
          📥 Descargar PDF (€29)
        </motion.button>

        {/* View Online */}
        <motion.a
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full bg-gray-200 hover:bg-gray-300 text-gray-900 font-semibold py-3 rounded-lg transition-all text-center"
        >
          👁️ Ver en pantalla
        </motion.a>

        {/* Start Over */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onStartOver}
          className="w-full bg-white border-2 border-gray-300 text-gray-700 font-semibold py-3 rounded-lg hover:border-gray-400 transition-all"
        >
          🔄 Repetir diagnóstico
        </motion.button>
      </motion.div>

      {/* Footer message */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
        className="text-sm text-gray-500 max-w-md mx-auto"
      >
        Este diagnóstico ha sido generado por un algoritmo adaptativo que analiza tu situación
        financiera desde múltiples ángulos. Es una herramienta educativa que te ayuda a entender
        tu posición y tomar mejores decisiones.
      </motion.p>
    </motion.div>
  );
};
