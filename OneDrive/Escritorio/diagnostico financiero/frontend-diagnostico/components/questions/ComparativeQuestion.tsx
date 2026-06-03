'use client';

import { motion } from 'framer-motion';
import { useDiagnostico } from '@/lib/store';

interface ComparativeQuestionProps {
  id: string;
  title: string;
  leftLabel: string;
  rightLabel: string;
  leftIcon?: string;
  rightIcon?: string;
}

export const ComparativeQuestion = ({
  id,
  title,
  leftLabel,
  rightLabel,
  leftIcon = '👈',
  rightIcon = '👉',
}: ComparativeQuestionProps) => {
  const { respuestas, setRespuesta } = useDiagnostico();
  const selected = (respuestas[id] as string) || null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full"
    >
      <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-8 text-center">{title}</h3>

        <div className="grid grid-cols-2 gap-4">
          {/* Left option */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setRespuesta(id, 'left')}
            className={`p-6 rounded-lg border-2 transition-all duration-200 ${
              selected === 'left'
                ? 'border-yellow-400 bg-yellow-50'
                : 'border-gray-200 bg-white hover:border-yellow-200'
            }`}
          >
            <div className="text-3xl mb-3">{leftIcon}</div>
            <div className="text-sm font-medium text-gray-700 text-center">{leftLabel}</div>
          </motion.button>

          {/* Right option */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setRespuesta(id, 'right')}
            className={`p-6 rounded-lg border-2 transition-all duration-200 ${
              selected === 'right'
                ? 'border-yellow-400 bg-yellow-50'
                : 'border-gray-200 bg-white hover:border-yellow-200'
            }`}
          >
            <div className="text-3xl mb-3">{rightIcon}</div>
            <div className="text-sm font-medium text-gray-700 text-center">{rightLabel}</div>
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
};
