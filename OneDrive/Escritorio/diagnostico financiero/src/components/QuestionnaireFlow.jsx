import React, { useState, useEffect, useCallback, useMemo } from 'react';

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

const SelectInput = React.memo(({ question, onAnswer, isAnswering }) => {
  return (
    <div className="space-y-3">
      {question.respuestas.map((option) => (
        <button
          key={option}
          onClick={() => !isAnswering && onAnswer(option)}
          disabled={isAnswering}
          className="w-full text-left p-4 border-2 border-gray-200 rounded-lg hover:border-indigo-600 hover:bg-indigo-50 transition font-medium text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {option}
        </button>
      ))}
    </div>
  );
});

SelectInput.displayName = 'SelectInput';

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

const SummaryDisplay = React.memo(({ responses, isAnswering, onSubmit }) => {
  return (
    <div className="space-y-4">
      <div className="bg-blue-50 p-4 rounded-lg">
        <h3 className="font-semibold text-gray-800 mb-4">Resumen de tus respuestas:</h3>
        <div className="max-h-96 overflow-y-auto space-y-2">
          {Object.entries(responses).slice(0, 20).map(([key, value]) => (
            <div key={key} className="text-sm text-gray-700">
              <span className="font-medium">{key}:</span> {String(value).substring(0, 50)}
            </div>
          ))}
          {Object.keys(responses).length > 20 && (
            <p className="text-xs text-gray-500 italic">...y {Object.keys(responses).length - 20} respuestas más</p>
          )}
        </div>
      </div>
      <button
        onClick={() => !isAnswering && onSubmit(responses)}
        disabled={isAnswering}
        className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition text-lg disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isAnswering ? 'Generando diagnóstico...' : 'Generar Diagnóstico'}
      </button>
    </div>
  );
});

SummaryDisplay.displayName = 'SummaryDisplay';

export default function QuestionnaireFlow() {
  const [allQuestions, setAllQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [responses, setResponses] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [isAnswering, setIsAnswering] = useState(false);
  const [questionHistory, setQuestionHistory] = useState([0]);
  const [error, setError] = useState(null);

  // Fetch questions from backend
  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        const response = await fetch('/api/v1/schema');
        const data = await response.json();
        setAllQuestions(data.questions);
        setIsLoading(false);
      } catch (err) {
        setError('Error al cargar las preguntas: ' + err.message);
        setIsLoading(false);
      }
    };

    fetchQuestions();
  }, []);

  const currentQuestion = useMemo(() => {
    if (allQuestions.length === 0) return null;
    return allQuestions[currentQuestionIndex];
  }, [allQuestions, currentQuestionIndex]);

  const progress = useMemo(() => {
    const totalQuestions = allQuestions.filter(q => q.type !== 'summary').length;
    const answeredQuestions = Object.keys(responses).length;
    return totalQuestions > 0 ? (answeredQuestions / totalQuestions) * 100 : 0;
  }, [allQuestions, responses]);

  const handleAnswer = useCallback((value) => {
    if (isAnswering) return;
    setIsAnswering(true);

    setTimeout(() => {
      const questionId = currentQuestion.id;
      const newResponses = { ...responses, [questionId]: value };
      setResponses(newResponses);

      // Find next question (for now, just increment)
      const nextIndex = currentQuestionIndex + 1;

      if (nextIndex >= allQuestions.length) {
        handleSubmit(newResponses);
      } else {
        setQuestionHistory([...questionHistory, nextIndex]);
        setCurrentQuestionIndex(nextIndex);
      }
      setIsAnswering(false);
    }, 100);
  }, [currentQuestionIndex, currentQuestion, responses, isAnswering, allQuestions, questionHistory]);

  const handleSubmit = useCallback(async (finalResponses) => {
    if (isAnswering) return;
    setIsAnswering(true);

    try {
      const response = await fetch('/api/v1/diagnose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers: finalResponses })
      });

      const data = await response.json();

      if (data.success) {
        // Download PDF
        const pdfPath = data.report_path;
        const pdfUrl = `/reports/${pdfPath.split('/').pop()}`;
        window.location.href = pdfUrl;
        alert('¡Diagnóstico completado! Tu reporte PDF está descargándose...');
      } else {
        alert('Error al generar el diagnóstico: ' + data.error);
      }
    } catch (err) {
      alert('Error al enviar respuestas: ' + err.message);
    } finally {
      setIsAnswering(false);
    }
  }, [isAnswering]);

  const handleBack = useCallback(() => {
    if (isAnswering || questionHistory.length <= 1) return;

    const newHistory = questionHistory.slice(0, -1);
    const previousIndex = newHistory[newHistory.length - 1];

    setQuestionHistory(newHistory);
    setCurrentQuestionIndex(previousIndex);
  }, [isAnswering, questionHistory]);

  if (isLoading) {
    return <div className="text-center p-8 min-h-screen flex items-center justify-center">
      <div className="space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
        <p className="text-gray-600">Cargando cuestionario...</p>
      </div>
    </div>;
  }

  if (error) {
    return <div className="text-center p-8 min-h-screen flex items-center justify-center">
      <div className="bg-red-50 p-6 rounded-lg border border-red-200">
        <p className="text-red-800 font-semibold">{error}</p>
      </div>
    </div>;
  }

  if (!currentQuestion) {
    return <div className="text-center p-8">No hay preguntas disponibles</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-2xl mx-auto mb-8">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            Diagnóstico Financiero Personalizado
          </h1>
          <p className="text-gray-600">Descubre tu situación financiera y recibe un plan a medida</p>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
        <p className="text-sm text-gray-600 mt-2 text-center">
          Progreso: {Math.round(progress)}% ({Object.keys(responses).length}/{allQuestions.filter(q => q.type !== 'summary').length})
        </p>
      </div>

      <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-8">
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            {currentQuestion.pregunta}
          </h2>
          {currentQuestion.description && (
            <p className="text-gray-600 text-sm">{currentQuestion.description}</p>
          )}
        </div>

        {currentQuestion.type === 'number' && (
          <NumberInput
            question={currentQuestion}
            onAnswer={handleAnswer}
            isAnswering={isAnswering}
          />
        )}

        {currentQuestion.type === 'select' && (
          <SelectInput
            question={currentQuestion}
            onAnswer={handleAnswer}
            isAnswering={isAnswering}
          />
        )}

        {currentQuestion.type === 'boolean' && (
          <BooleanInput
            onAnswer={handleAnswer}
            isAnswering={isAnswering}
          />
        )}

        {currentQuestion.type === 'text' && (
          <TextInput
            onAnswer={handleAnswer}
            isAnswering={isAnswering}
          />
        )}

        {currentQuestion.type === 'summary' && (
          <SummaryDisplay
            responses={responses}
            isAnswering={isAnswering}
            onSubmit={handleSubmit}
          />
        )}

        {currentQuestion.type !== 'summary' && (
          <button
            onClick={handleBack}
            disabled={isAnswering}
            className="mt-6 text-indigo-600 hover:text-indigo-800 font-medium text-sm disabled:opacity-50"
          >
            ← Volver atrás
          </button>
        )}
      </div>

      <div className="max-w-2xl mx-auto mt-8 text-center text-gray-600 text-sm">
        <p>Tu información es 100% confidencial y segura.</p>
      </div>
    </div>
  );
}
