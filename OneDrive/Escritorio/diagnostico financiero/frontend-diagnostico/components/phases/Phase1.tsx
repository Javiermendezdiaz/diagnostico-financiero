'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDiagnostico } from '@/lib/store';
import { SliderQuestion } from '@/components/questions/SliderQuestion';
import { ToggleGridQuestion } from '@/components/questions/ToggleGridQuestion';
import { ScaleQuestion } from '@/components/questions/ScaleQuestion';
import { ComparativeQuestion } from '@/components/questions/ComparativeQuestion';
import { ProgressVisualization } from '@/components/insights/ProgressVisualization';
import { TransitionCard } from '@/components/insights/TransitionCard';
import { InsightCard } from '@/components/insights/InsightCard';

const FASE1_PREGUNTAS = [
  {
    id: 'ingresos_netos',
    type: 'slider',
    title: '¿Cuál es tu ingreso neto mensual? (€)',
    min: 500,
    max: 10000,
    step: 100,
    suffix: '€',
  },
  {
    id: 'gastos_totales',
    type: 'slider',
    title: '¿Cuánto gastas al mes? (€)',
    min: 500,
    max: 10000,
    step: 100,
    suffix: '€',
  },
  {
    id: 'saldo_hipoteca',
    type: 'slider',
    title: '¿Cuál es tu deuda hipotecaria? (€)',
    min: 0,
    max: 500000,
    step: 10000,
    suffix: '€',
  },
  {
    id: 'saldo_tarjetas',
    type: 'slider',
    title: '¿Cuánto debes en tarjetas de crédito? (€)',
    min: 0,
    max: 50000,
    step: 500,
    suffix: '€',
  },
  {
    id: 'ahorros_totales',
    type: 'slider',
    title: '¿Cuánto tienes ahorrado? (€)',
    min: 0,
    max: 100000,
    step: 1000,
    suffix: '€',
  },
  {
    id: 'tiene_hijos',
    type: 'toggle',
    title: '¿Tienes hijos o personas a cargo?',
    options: ['No', 'Sí'],
    icons: ['👤', '👨‍👩‍👧‍👦'],
    multiple: false,
  },
  {
    id: 'ingresos_variables',
    type: 'toggle',
    title: '¿Tus ingresos son variables o irregulares?',
    options: ['No, fijos', 'Parcialmente', 'Sí, muy variables'],
    multiple: false,
  },
  {
    id: 'pareja_ingresos',
    type: 'toggle',
    title: '¿Tienes pareja con ingresos?',
    options: ['No tengo pareja', 'Pareja sin ingresos', 'Pareja con ingresos'],
    multiple: false,
  },
  {
    id: 'pago_hipoteca_mensual',
    type: 'slider',
    title: '¿Cuánto pagas de hipoteca al mes? (€)',
    min: 0,
    max: 3000,
    step: 50,
    suffix: '€',
  },
  {
    id: 'pago_minimo_tarjeta',
    type: 'slider',
    title: '¿Cuál es tu pago mínimo en tarjeta? (€)',
    min: 0,
    max: 1000,
    step: 25,
    suffix: '€',
  },
  {
    id: 'pago_otros_prestamos',
    type: 'slider',
    title: '¿Cuánto pagas en otros préstamos? (€)',
    min: 0,
    max: 2000,
    step: 50,
    suffix: '€',
  },
  {
    id: 'inversiones',
    type: 'toggle',
    title: '¿Tienes inversiones o fondos?',
    options: ['No', 'Sí, algunas', 'Sí, activas'],
    multiple: false,
  },
  {
    id: 'seguros_vida',
    type: 'toggle',
    title: '¿Tienes seguros de vida?',
    options: ['No', 'Sí'],
    multiple: false,
  },
  {
    id: 'patrimonio_total',
    type: 'slider',
    title: '¿Cuál es tu patrimonio total? (€)',
    min: 0,
    max: 1000000,
    step: 10000,
    suffix: '€',
  },
  {
    id: 'situacion_actual',
    type: 'toggle',
    title: '¿Cómo describes tu situación financiera actual?',
    options: ['Abrumada', 'Estancada', 'Estable', 'Optimista'],
    icons: ['😰', '😐', '🙂', '😄'],
    multiple: false,
  },
  {
    id: 'prioridad_cambio',
    type: 'toggle',
    title: '¿Cuál es tu prioridad principal?',
    options: ['Sobrevivir', 'Ahorrar', 'Invertir', 'Planificar'],
    multiple: true,
  },
  {
    id: 'riesgo_disposicion',
    type: 'scale',
    title: '¿Cuál es tu disposición al riesgo financiero?',
    min: 1,
    max: 10,
    minLabel: 'Cero riesgo',
    maxLabel: 'Alto riesgo',
  },
  {
    id: 'control_gastos',
    type: 'scale',
    title: '¿Qué control tienes sobre tus gastos?',
    min: 1,
    max: 10,
    minLabel: 'Sin control',
    maxLabel: 'Control total',
  },
  {
    id: 'educacion_financiera',
    type: 'scale',
    title: '¿Cuál es tu nivel de educación financiera?',
    min: 1,
    max: 10,
    minLabel: 'Principiante',
    maxLabel: 'Experto',
  },
  {
    id: 'stress_nivel',
    type: 'scale',
    title: '¿Cuál es tu nivel de estrés por dinero?',
    min: 1,
    max: 10,
    minLabel: 'Relajado',
    maxLabel: 'Agobiado',
  },
  {
    id: 'compatibilidad_pareja',
    type: 'scale',
    title: '¿Hay acuerdo con tu pareja en finanzas?',
    min: 1,
    max: 10,
    minLabel: 'Total desacuerdo',
    maxLabel: 'Acuerdo completo',
  },
  {
    id: 'fondo_emergencia',
    type: 'comparative',
    title: '¿Tienes fondo de emergencia?',
    leftLabel: 'No',
    rightLabel: 'Sí',
    leftIcon: '❌',
    rightIcon: '✅',
  },
  {
    id: 'deuda_tiempo_pago',
    type: 'toggle',
    title: '¿En cuánto tiempo podrías pagar tu deuda?',
    options: ['5+ años', '3-5 años', '1-3 años', 'Menos de 1 año'],
    multiple: false,
  },
  {
    id: 'cambio_disposicion',
    type: 'scale',
    title: '¿Estás dispuesto a cambiar tus hábitos?',
    min: 1,
    max: 10,
    minLabel: 'No cambiaría',
    maxLabel: 'Cambio total',
  },
  {
    id: 'objetivo_5_anos',
    type: 'toggle',
    title: '¿Cuál es tu objetivo en 5 años?',
    options: ['Estabilidad', 'Libertad', 'Riqueza', 'Seguridad familiar'],
    icons: ['🏠', '✈️', '💰', '👨‍👩‍👧‍👦'],
    multiple: true,
  },
];

interface Phase1Props {
  onPhase2Ready: (perfil: string, fase2Preguntas: any[]) => void;
}

export const Phase1 = ({ onPhase2Ready }: Phase1Props) => {
  const { respuestas, setRespuesta, avanzarFase, setPerfil, setFase2Preguntas } =
    useDiagnostico();
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [showTransition, setShowTransition] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const currentQuestion = FASE1_PREGUNTAS[currentQuestionIdx];
  const progress = ((currentQuestionIdx + 1) / FASE1_PREGUNTAS.length) * 100;

  const handleNext = async () => {
    if (currentQuestionIdx < FASE1_PREGUNTAS.length - 1) {
      setCurrentQuestionIdx(currentQuestionIdx + 1);
    } else {
      setIsLoading(true);
      try {
        // Call backend to detect profile and get Phase 2 questions
        const { data } = await (await import('@/lib/api-client')).apiClient.generarFase2(respuestas);
        setPerfil(data.perfil);
        setFase2Preguntas(data.fase2_preguntas);
        setShowTransition(true);
      } catch (error) {
        console.error('Error generating Phase 2:', error);
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
    switch (currentQuestion.type) {
      case 'slider':
        return (
          <SliderQuestion
            id={currentQuestion.id}
            title={currentQuestion.title}
            min={currentQuestion.min}
            max={currentQuestion.max}
            step={currentQuestion.step}
            suffix={currentQuestion.suffix}
          />
        );
      case 'toggle':
        return (
          <ToggleGridQuestion
            id={currentQuestion.id}
            title={currentQuestion.title}
            options={currentQuestion.options}
            icons={currentQuestion.icons}
            multiple={currentQuestion.multiple}
          />
        );
      case 'scale':
        return (
          <ScaleQuestion
            id={currentQuestion.id}
            title={currentQuestion.title}
            min={currentQuestion.min}
            max={currentQuestion.max}
            minLabel={currentQuestion.minLabel}
            maxLabel={currentQuestion.maxLabel}
          />
        );
      case 'comparative':
        return (
          <ComparativeQuestion
            id={currentQuestion.id}
            title={currentQuestion.title}
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
        title="¡Fase 1 completada! 🎯"
        description="Hemos detectado tu perfil financiero. Ahora vamos a personalizar las preguntas según tu situación."
        nextPhase={2}
        onContinue={() => {
          avanzarFase();
          onPhase2Ready(respuestas.perfil as string, respuestas.fase2Preguntas as any[]);
        }}
      />
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Progress */}
      <ProgressVisualization
        currentFase={1}
        fase1Progress={progress}
        fase2Progress={0}
        fase3Progress={0}
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
          {currentQuestionIdx + 1} / {FASE1_PREGUNTAS.length}
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
