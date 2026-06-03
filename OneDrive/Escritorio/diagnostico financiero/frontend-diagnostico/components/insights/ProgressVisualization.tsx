'use client';

import { motion } from 'framer-motion';

interface ProgressVisualizationProps {
  currentFase: 1 | 2 | 3 | 'resultado';
  fase1Progress: number; // 0-100
  fase2Progress: number; // 0-100
  fase3Progress: number; // 0-100
  estimatedTime?: string;
}

export const ProgressVisualization = ({
  currentFase,
  fase1Progress,
  fase2Progress,
  fase3Progress,
  estimatedTime = '~12 min',
}: ProgressVisualizationProps) => {
  const phases = [
    { label: 'Fase 1', icon: '🏗️', desc: 'Cimientos', progress: fase1Progress },
    { label: 'Fase 2', icon: '🔀', desc: 'Dinámico', progress: fase2Progress },
    { label: 'Fase 3', icon: '🧠', desc: 'Psicología', progress: fase3Progress },
  ];

  return (
    <div className="w-full bg-white rounded-lg p-6 shadow-sm border border-gray-100">
      {/* Timeline */}
      <div className="mb-8">
        <div className="flex justify-between items-center mb-6">
          {phases.map((phase, idx) => (
            <div key={idx} className="flex flex-col items-center flex-1">
              <motion.div
                animate={{
                  scale:
                    (currentFase === idx + 1 || currentFase === 'resultado') ? 1.1 : 1,
                }}
                className={`w-12 h-12 rounded-full flex items-center justify-center font-bold mb-2 transition-all duration-300 ${
                  (currentFase === idx + 1 || currentFase === 'resultado')
                    ? 'bg-yellow-400 text-gray-900'
                    : 'bg-gray-200 text-gray-700'
                }`}
              >
                {phase.icon}
              </motion.div>
              <p className="text-xs font-semibold text-gray-700">{phase.label}</p>
              <p className="text-xs text-gray-500">{phase.desc}</p>
            </div>
          ))}
        </div>

        {/* Connecting line */}
        <div className="flex gap-2">
          {[0, 1, 2].map((idx) => (
            <div key={idx} className="flex-1">
              <motion.div
                animate={{
                  backgroundColor:
                    currentFase === 'resultado' ||
                    (typeof currentFase === 'number' && currentFase > idx + 1)
                      ? '#FDD731'
                      : '#E5E7EB',
                }}
                className="h-1 rounded-full"
                transition={{ duration: 0.3 }}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Progress bars */}
      <div className="space-y-4">
        {phases.map((phase, idx) => (
          <div key={idx}>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-700">{phase.label}</span>
              <span className="text-xs text-yellow-600 font-semibold">
                {Math.round(phase.progress)}%
              </span>
            </div>
            <motion.div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
              <motion.div
                animate={{ width: `${phase.progress}%` }}
                transition={{ duration: 0.5, ease: 'easeInOut' }}
                className="h-full bg-yellow-400"
              />
            </motion.div>
          </div>
        ))}
      </div>

      {/* Estimated time */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          ⏱️ Tiempo estimado: <span className="font-semibold text-gray-700">{estimatedTime}</span>
        </p>
      </div>
    </div>
  );
};
