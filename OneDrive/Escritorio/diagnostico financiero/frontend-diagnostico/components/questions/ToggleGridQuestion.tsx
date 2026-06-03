'use client';

import { motion } from 'framer-motion';
import { useDiagnostico } from '@/lib/store';

interface ToggleGridQuestionProps {
  id: string;
  title: string;
  options: string[];
  icons?: string[];
  multiple?: boolean;
}

export const ToggleGridQuestion = ({
  id,
  title,
  options,
  icons = [],
  multiple = true,
}: ToggleGridQuestionProps) => {
  const { respuestas, setRespuesta } = useDiagnostico();
  const selectedValues = (respuestas[id] as string[]) || [];

  const handleToggle = (option: string) => {
    if (multiple) {
      const updated = selectedValues.includes(option)
        ? selectedValues.filter((v) => v !== option)
        : [...selectedValues, option];
      setRespuesta(id, updated);
    } else {
      setRespuesta(id, selectedValues[0] === option ? [] : [option]);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full"
    >
      <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-6">{title}</h3>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {options.map((option, idx) => (
            <motion.button
              key={option}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => handleToggle(option)}
              className={`p-4 rounded-lg border-2 transition-all duration-200 ${
                selectedValues.includes(option)
                  ? 'border-yellow-400 bg-yellow-50'
                  : 'border-gray-200 bg-white hover:border-yellow-200'
              }`}
            >
              <div className="text-2xl mb-2">{icons[idx] || '✓'}</div>
              <div className="text-sm font-medium text-gray-700">{option}</div>
            </motion.button>
          ))}
        </div>
      </div>
    </motion.div>
  );
};
