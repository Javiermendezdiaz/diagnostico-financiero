'use client';

import { motion } from 'framer-motion';

interface InsightCardProps {
  title: string;
  subtitle?: string;
  content: string;
  icon?: string;
  severity?: 'info' | 'warning' | 'critical' | 'success';
}

export const InsightCard = ({
  title,
  subtitle,
  content,
  icon = '💡',
  severity = 'info',
}: InsightCardProps) => {
  const severityStyles = {
    info: 'bg-blue-50 border-blue-200 text-blue-900',
    warning: 'bg-orange-50 border-orange-200 text-orange-900',
    critical: 'bg-red-50 border-red-200 text-red-900',
    success: 'bg-green-50 border-green-200 text-green-900',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={`rounded-lg border-2 p-6 ${severityStyles[severity]}`}
    >
      <div className="flex items-start gap-4">
        <div className="text-3xl flex-shrink-0">{icon}</div>
        <div className="flex-1">
          <h4 className="font-semibold text-lg mb-1">{title}</h4>
          {subtitle && <p className="text-sm opacity-75 mb-3">{subtitle}</p>}
          <p className="text-sm leading-relaxed">{content}</p>
        </div>
      </div>
    </motion.div>
  );
};
