'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDiagnostico } from '@/lib/store';
import { SliderQuestion } from '@/components/questions/SliderQuestion';
import { ToggleGridQuestion } from '@/components/questions/ToggleGridQuestion';
import { ScaleQuestion } from '@/components/questions/ScaleQuestion';
import { ComparativeQuestion } from '@/components/questions/ComparativeQuestion';
import { ProgressVisualization } from '@/components/insights/ProgressVisualization';
import { TransitionCard } from '@/components/insights/TransitionCard';
import { InsightCard } from '@/components/insights/InsightCard';

interface Phase2Props {
  preguntas: any[];
  onPhase3Ready: () => void;
}

export const Phase2 = ({ preguntas, onPhase3Ready }: Phase2Props) => {
  const { respuestas, setRespuesta, avanzarFase, setFase3Preguntas } = useDiagnostico();
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [showTransition, setShowTransition] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const currentQuestion = preguntas[currentQuestionIdx];
  const progress = ((currentQuestionIdx + 1) / preguntas.length) * 100;

  const handleNext = async () => {
    if (currentQuestionIdx < preguntas.length - 1) {
      setCurrentQuestionIdx(currentQuestionIdx + 1);
    } else {
      setIsLoading(true);
      try {
        // Call backend to get Phase 3 questions
        const { data } = await (await import('@/lib/api-client')).apiClient.generarFase3(respuestas);
        setFase3Preguntas(data.fase3_preguntas);
        setShowTransition(true);
      } catch (error) {
        console.error('Error generating Phase 3:', error);
        alert('Error generando preguntas. Por favor, intenta de nuevo.');
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIdx > 0) {
      setCurrentQuestionIdx(currentQuestionIdx - 1);
    }
  };

  const renderQuestion = () => {
    const { type, title, options, icons, multiple, min, max, step, suffix, minLabel, maxLabel } =
      currentQuestion;

    switch (type) {
      case 'slider':
        return (
          <SliderQuestion
            id={currentQuestion.id}
            title={title}
            min={min || 0}
            max={max || 100}
            step={step || 1}
            suffix={suffix || ''}
          />
        );
      case 'toggle':
        return (
          <ToggleGridQuestion
            id={currentQuestion.id}
            title={title}
            options={options || []}
            icons={icons}
            multiple={multiple}
          />
        );
      case 'scale':
        return (
          <ScaleQuestion
            id={currentQuestion.id}
            title={title}
            min={min || 1}
            max={max || 10}
            minLabel={minLabel}
            maxLabel={maxLabel}
          />
        );
      case 'comparative':
        return (
          <ComparativeQuestion
            id={currentQuestion.id}
            title={title}
            leftLabel={currentQuestion.leftLabel}
            rightLabel={currentQuestion.rightLabel}
            leftIcon={currentQuestion.leftIcon}
            rightIcon={currentQuestion.rightIcon}
          />
        );
      default:
        return null;
    }
  };

  if (showTransition) {
    return (
      <TransitionCard
        title="¡Fase 2 completada! ⚡"
        description="Tus respuestas nos han dado una visión clara de tu situación. Ahora vamos a explorar los aspectos psicológicos."
        nextPhase={3}
        onContinue={() => {
          avanzarFase();
          onPhase3Ready();
        }}
      />
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Progress */}
      <ProgressVisualization
        currentFase={2}
        fase1Progress={100}
        fase2Progress={progress}
        fase3Progress={0}
      />

      {/* Insight */}
      <InsightCard
        title="Preguntas personalizadas"
        subtitle="Basadas en tu perfil financiero"
        content="Estas preguntas se han seleccionado específicamente según tu situación. No hay respuestas correctas o incorrectas."
        icon="🎯"
        severity="info"
      />

      {/* Current question */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentQuestionIdx}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          {renderQuestion()}
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div className="flex gap-3 justify-between">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handlePrevious}
          disabled={currentQuestionIdx === 0}
          className="px-6 py-2 rounded-lg border-2 border-gray-300 text-gray-700 font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:border-gray-400 transition-all"
        >
          ← Atrás
        </motion.button>

        <div className="text-sm text-gray-600 flex items-center">
          {currentQuestionIdx + 1} / {preguntas.length}
        </div>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleNext}
          disabled={isLoading}
          className="px-6 py-2 rounded-lg bg-yellow-400 text-gray-900 font-semibold hover:bg-yellow-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Procesando...' : 'Siguiente →'}
        </motion.button>
      </div>

      {/* Progress bar */}
      <motion.div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <motion.div
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: 'easeInOut' }}
          className="h-full bg-yellow-400"
        />
      </motion.div>
    </div>
  );
};
