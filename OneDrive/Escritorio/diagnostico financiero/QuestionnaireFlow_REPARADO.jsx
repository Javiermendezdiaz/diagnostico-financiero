import React, { useState, useEffect, useCallback, useMemo } from 'react';
import questionnaireData from './questionnaire-structure.json';

// Debounce helper
const debounce = (func, delay) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};

// Separate component for Number Input to avoid memory leaks
const NumberInput = React.memo(({ question, onAnswer, isAnswering }) => {
  const inputRef = React.useRef(null);

  const handleClick = useCallback(() => {
    if (inputRef.current && inputRef.current.value && !isAnswering) {
      onAnswer(parseFloat(inputRef.current.value));
    }
  }, [onAnswer, isAnswering]);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && inputRef.current && inputRef.current.value && !isAnswering) {
      onAnswer(parseFloat(inputRef.current.value));
    }
  }, [onAnswer, isAnswering]);

  return (
    <div className="mb-6">
      <input
        ref={inputRef}
        type="number"
        min={question.min}
        max={question.max}
        placeholder="Ingresa el valor"
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
        onKeyPress={handleKeyPress}
        disabled={isAnswering}
        autoFocus
      />
      <button
        onClick={handleClick}
        disabled={isAnswering}
        className="mt-4 w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isAnswering ? 'Procesando...' : 'Continuar'}
      </button>
    </div>
  );
});

NumberInput.displayName = 'NumberInput';

// Separate component for Select Input
const SelectInput = React.memo(({ question, onAnswer, isAnswering }) => {
  return (
    <div className="space-y-3">
      {question.options.map((option) => (
        <button
          key={option.value}
          onClick={() => !isAnswering && onAnswer(option.value)}
          disabled={isAnswering}
          className="w-full text-left p-4 border-2 border-gray-200 rounded-lg hover:border-indigo-600 hover:bg-indigo-50 transition font-medium text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
});

SelectInput.displayName = 'SelectInput';

// Separate component for Boolean Input
const BooleanInput = React.memo(({ onAnswer, isAnswering }) => {
  return (
    <div className="grid grid-cols-2 gap-4">
      <button
        onClick={() => !isAnswering && onAnswer(true)}
        disabled={isAnswering}
        className="p-4 border-2 border-green-200 rounded-lg hover:border-green-600 hover:bg-green-50 transition font-semibold text-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Sí
      </button>
      <button
        onClick={() => !isAnswering && onAnswer(false)}
        disabled={isAnswering}
        className="p-4 border-2 border-red-200 rounded-lg hover:border-red-600 hover:bg-red-50 transition font-semibold text-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        No
      </button>
    </div>
  );
});

BooleanInput.displayName = 'BooleanInput';

// Separate component for Text Input
const TextInput = React.memo(({ onAnswer, isAnswering }) => {
  const textareaRef = React.useRef(null);

  const handleClick = useCallback(() => {
    if (textareaRef.current && textareaRef.current.value && !isAnswering) {
      onAnswer(textareaRef.current.value);
    }
  }, [onAnswer, isAnswering]);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && e.ctrlKey && textareaRef.current && textareaRef.current.value && !isAnswering) {
      onAnswer(textareaRef.current.value);
    }
  }, [onAnswer, isAnswering]);

  return (
    <div className="mb-6">
      <textarea
        ref={textareaRef}
        placeholder="Escribe tu respuesta aquí..."
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
        rows="4"
        onKeyPress={handleKeyPress}
        disabled={isAnswering}
        autoFocus
      />
      <p className="text-xs text-gray-500 mt-2">Presiona Ctrl+Enter para continuar</p>
      <button
        onClick={handleClick}
        disabled={isAnswering}
        className="mt-4 w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isAnswering ? 'Procesando...' : 'Continuar'}
      </button>
    </div>
  );
});

TextInput.displayName = 'TextInput';

// Separate component for Summary Display
const SummaryDisplay = React.memo(({ responses, isAnswering, onSubmit }) => {
  return (
    <div className="space-y-4">
      <div className="bg-blue-50 p-4 rounded-lg">
        <h3 className="font-semibold text-gray-800 mb-4">Resumen de tus respuestas:</h3>
        <div className="max-h-96 overflow-y-auto space-y-2">
          {Object.entries(responses).map(([key, value]) => (
            <div key={key} className="text-sm text-gray-700">
              <span className="font-medium">{key}:</span> {String(value).substring(0, 50)}...
            </div>
          ))}
        </div>
      </div>
      <button
        onClick={() => !isAnswering && onSubmit(responses)}
        disabled={isAnswering}
        className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition text-lg disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isAnswering ? 'Procesando...' : 'Generar Diagnóstico'}
      </button>
    </div>
  );
});

SummaryDisplay.displayName = 'SummaryDisplay';

export default function QuestionnaireFlow() {
  const [currentQuestionId, setCurrentQuestionId] = useState('age');
  const [responses, setResponses] = useState({});
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [progress, setProgress] = useState(0);
  const [isAnswering, setIsAnswering] = useState(false);
  const [questionHistory, setQuestionHistory] = useState(['age']);

  // Memoize question map for efficient lookups
  const questionMap = useMemo(() => {
    const map = new Map();
    questionnaireData.questionnaire.flow.forEach(q => {
      map.set(q.id, q);
    });
    return map;
  }, []);

  // Get question by ID (memoized)
  const getQuestion = useCallback((id) => {
    return questionMap.get(id);
  }, [questionMap]);

  // Calculate progress percentage (memoized, only when responses change)
  const calculateProgress = useCallback(() => {
    const totalQuestions = questionnaireData.questionnaire.flow.filter(q => q.type !== 'summary').length;
    const answeredQuestions = Object.keys(responses).length;
    return (answeredQuestions / totalQuestions) * 100;
  }, []);

  // Update progress only when responses change
  useEffect(() => {
    setProgress(calculateProgress());
  }, [responses, calculateProgress]);

  // Initialize first question - with cleanup
  useEffect(() => {
    const question = getQuestion(currentQuestionId);
    setCurrentQuestion(question);

    // Cleanup function
    return () => {
      // Clear any pending state updates if component unmounts
      setCurrentQuestion(null);
    };
  }, [currentQuestionId, getQuestion]);

  // Handle answer and move to next question (memoized + debounced)
  const handleAnswer = useCallback((value) => {
    // Prevent rapid consecutive answers
    if (isAnswering) return;
    setIsAnswering(true);

    setTimeout(() => {
      const newResponses = { ...responses, [currentQuestionId]: value };
      setResponses(newResponses);

      const question = getQuestion(currentQuestionId);
      if (!question) {
        console.error('Question not found:', currentQuestionId);
        setIsAnswering(false);
        return;
      }

      let nextQuestionId = question.nextQuestion;

      // Handle conditional logic
      if (question.conditional) {
        nextQuestionId = question.conditional[value] || question.nextQuestion;
      }

      if (nextQuestionId === 'end') {
        handleSubmit(newResponses);
      } else {
        setQuestionHistory([...questionHistory, nextQuestionId]);
        setCurrentQuestionId(nextQuestionId);
      }
      setIsAnswering(false);
    }, 100); // 100ms debounce
  }, [currentQuestionId, responses, isAnswering, getQuestion, questionHistory]);

  // Submit responses (memoized)
  const handleSubmit = useCallback(async (finalResponses) => {
    if (isAnswering) return;
    setIsAnswering(true);
    console.log('Submitting responses:', finalResponses);
    // TODO: Send to backend/Firebase
    alert('¡Diagnóstico completado! Procesando tu información...');
    setIsAnswering(false);
  }, [isAnswering]);

  // Go back to previous question (memoized)
  const handleBack = useCallback(() => {
    if (isAnswering || questionHistory.length <= 1) return;

    // Remove current question from history and go back to previous
    const newHistory = questionHistory.slice(0, -1);
    const previousQuestionId = newHistory[newHistory.length - 1];

    setQuestionHistory(newHistory);
    setCurrentQuestionId(previousQuestionId);
  }, [isAnswering, questionHistory]);

  if (!currentQuestion) {
    return <div className="text-center p-8">Cargando...</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      {/* Header */}
      <div className="max-w-2xl mx-auto mb-8">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            Diagnóstico Financiero Personalizado
          </h1>
          <p className="text-gray-600">Descubre tu situación financiera y recibe un plan a medida</p>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
        <p className="text-sm text-gray-600 mt-2 text-center">
          Progreso: {Math.round(progress)}%
        </p>
      </div>

      {/* Question Container */}
      <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-8">
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            {currentQuestion.label}
          </h2>
          {currentQuestion.description && (
            <p className="text-gray-600 text-sm">{currentQuestion.description}</p>
          )}
        </div>

        {/* Question Type: Number Input */}
        {currentQuestion.type === 'number' && (
          <NumberInput
            question={currentQuestion}
            onAnswer={handleAnswer}
            isAnswering={isAnswering}
          />
        )}

        {/* Question Type: Select */}
        {currentQuestion.type === 'select' && (
          <SelectInput
            question={currentQuestion}
            onAnswer={handleAnswer}
            isAnswering={isAnswering}
          />
        )}

        {/* Question Type: Boolean */}
        {currentQuestion.type === 'boolean' && (
          <BooleanInput
            onAnswer={handleAnswer}
            isAnswering={isAnswering}
          />
        )}

        {/* Question Type: Text */}
        {currentQuestion.type === 'text' && (
          <TextInput
            onAnswer={handleAnswer}
            isAnswering={isAnswering}
          />
        )}

        {/* Question Type: Summary */}
        {currentQuestion.type === 'summary' && (
          <SummaryDisplay
            responses={responses}
            isAnswering={isAnswering}
            onSubmit={handleSubmit}
          />
        )}

        {/* Back Button */}
        {currentQuestion.type !== 'summary' && (
          <button
            onClick={handleBack}
            className="mt-6 text-indigo-600 hover:text-indigo-800 font-medium text-sm"
          >
            ← Volver atrás
          </button>
        )}
      </div>

      {/* Footer */}
      <div className="max-w-2xl mx-auto mt-8 text-center text-gray-600 text-sm">
        <p>Tu información es 100% confidencial y segura.</p>
      </div>
    </div>
  );
}
