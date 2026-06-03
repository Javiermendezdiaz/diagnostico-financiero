'use client';

import { useState, useEffect } from 'react';
import { useDiagnostico } from '@/lib/store';
import { Phase1 } from '@/components/phases/Phase1';
import { Phase2 } from '@/components/phases/Phase2';
import { Phase3 } from '@/components/phases/Phase3';
import { ResultPage } from '@/components/results/ResultPage';
import { motion } from 'framer-motion';

export const QuestionnaireFlow = () => {
  const { fase, fase2Preguntas, fase3Preguntas, pdfUrl, reset } = useDiagnostico();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initialize
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity }}
          className="w-12 h-12 border-4 border-yellow-400 border-t-transparent rounded-full"
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto p-6 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Diagnóstico Financiero
          </h1>
          <p className="text-gray-600">Descubre tu situación real en 15 minutos</p>
        </motion.div>

        {/* Content */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          {fase === 1 && (
            <Phase1
              onPhase2Ready={() => {
                // Phase 2 will auto-advance when backend responds
              }}
            />
          )}

          {fase === 2 && fase2Preguntas.length > 0 && (
            <Phase2
              preguntas={fase2Preguntas}
              onPhase3Ready={() => {
                // Phase 3 will auto-advance when backend responds
              }}
            />
          )}

          {fase === 3 && fase3Preguntas.length > 0 && (
            <Phase3
              preguntas={fase3Preguntas}
              onResultado={() => {
                // Result page will auto-show when PDF is ready
              }}
            />
          )}

          {fase === 'resultado' && pdfUrl && (
            <ResultPage
              pdfUrl={pdfUrl}
              onStartOver={() => {
                reset();
              }}
            />
          )}
        </motion.div>
      </div>
    </div>
  );
};
