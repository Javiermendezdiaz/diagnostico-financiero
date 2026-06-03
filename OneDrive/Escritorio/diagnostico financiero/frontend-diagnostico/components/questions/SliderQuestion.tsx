'use client';

import { motion } from 'framer-motion';
import { useDiagnostico } from '@/lib/store';

interface SliderQuestionProps {
  id: string;
  title: string;
  min: number;
  max: number;
  step: number;
  suffix: string;
  defaultValue?: number;
}

export const SliderQuestion = ({
  id,
  title,
  min,
  max,
  step,
  suffix,
  defaultValue = min,
}: SliderQuestionProps) => {
  const { respuestas, setRespuesta } = useDiagnostico();
  const value = respuestas[id] || defaultValue;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full"
    >
      <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-6">{title}</h3>

        <div className="space-y-4">
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => setRespuesta(id, parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-yellow-400"
          />

          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">{min.toLocaleString()} {suffix}</span>
            <div className="text-center">
              <div className="text-3xl font-bold text-yellow-500">{value}</div>
              <div className="text-xs text-gray-400">{suffix}</div>
            </div>
            <span className="text-sm text-gray-500">{max.toLocaleString()} {suffix}</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
