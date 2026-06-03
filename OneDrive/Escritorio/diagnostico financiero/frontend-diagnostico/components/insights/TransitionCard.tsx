'use client';

import { motion } from 'framer-motion';
import confetti from 'canvas-confetti';

interface TransitionCardProps {
  title: string;
  description: string;
  nextPhase: number;
  onContinue: () => void;
  showConfetti?: boolean;
}

export const TransitionCard = ({
  title,
  description,
  nextPhase,
  onContinue,
  showConfetti = true,
}: TransitionCardProps) => {
  const triggerConfetti = () => {
    if (showConfetti) {
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
      });
    }
    onContinue();
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-md mx-auto"
    >
      <div className="bg-gradient-to-br from-yellow-400 to-yellow-300 rounded-lg p-8 shadow-lg text-center">
        <motion.div
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 0.6, repeat: Infinity, repeatDelay: 2 }}
          className="text-5xl mb-6"
        >
          ⭐
        </motion.div>

        <h2 className="text-2xl font-bold text-gray-900 mb-3">{title}</h2>
        <p className="text-gray-800 text-sm mb-8 leading-relaxed">{description}</p>

        <div className="mb-8 p-4 bg-white rounded-lg">
          <p className="text-sm text-gray-600">
            Siguiente: <span className="font-bold text-yellow-600">Fase {nextPhase}</span>
          </p>
        </div>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={triggerConfetti}
          className="w-full bg-gray-900 hover:bg-gray-800 text-yellow-400 font-bold py-3 rounded-lg transition-all duration-200"
        >
          Continuar →
        </motion.button>
      </div>
    </motion.div>
  );
};
