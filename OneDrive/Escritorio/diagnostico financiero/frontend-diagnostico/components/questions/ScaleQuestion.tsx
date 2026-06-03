'use client';

import { motion } from 'framer-motion';
import { useDiagnostico } from '@/lib/store';

interface ScaleQuestionProps {
  id: string;
  title: string;
  min: number;
  max: number;
  minLabel?: string;
  maxLabel?: string;
  emoji?: string[];
}

export const ScaleQuestion = ({
  id,
  title,
  min = 1,
  max = 10,
  minLabel = 'Muy bajo',
  maxLabel = 'Muy alto',
  emoji = ['😞', '😟', '😐', '🙂', '😊', '😄', '😃', '😄', '😊', '🤩'],
}: ScaleQuestionProps) => {
  const { respuestas, setRespuesta } = useDiagnostico();
  const value = (respuestas[id] as number) || min;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full"
    >
      <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-8">{title}</h3>

        <div className="space-y-6">
          {/* Emoji feedback */}
          <div className="flex justify-center">
            <motion.div
              key={value}
              animate={{ scale: [0.8, 1.2, 1] }}
              transition={{ duration: 0.3 }}
              className="text-6xl"
            >
              {emoji[value - min] || '🤔'}
            </motion.div>
          </div>

          {/* Scale buttons */}
          <div className="flex gap-2 justify-between">
            {Array.from({ length: max - min + 1 }, (_, i) => min + i).map(
              (num) => (
                <motion.button
                  key={num}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setRespuesta(id, num)}
                  className={`h-10 w-10 rounded-full font-semibold transition-all duration-200 ${
                    value === num
                      ? 'bg-yellow-400 text-gray-900 shadow-lg'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {num}
                </motion.button>
              )
            )}
          </div>

          {/* Labels */}
          <div className="flex justify-between text-xs text-gray-500 font-medium">
            <span>{minLabel}</span>
            <span>{maxLabel}</span>
          </div>

          {/* Current value display */}
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-500">{value}</div>
            <div className="text-xs text-gray-400 mt-1">de {max}</div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
