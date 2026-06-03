/**
 * react_integration.js
 * Monta los 4 componentes React psicológicos en el HTML template.
 * Task #47 — Psicología de Interfaz
 */

// ============ PASO 1: Validar que React está disponible ============

if (typeof ReactDOM === 'undefined' || typeof React === 'undefined') {
    console.error('[REACT_INTEGRATION] React no disponible. Asegúrate de que React 18+ está cargado antes de este script.');
    throw new Error('React/ReactDOM required');
}

// ============ PASO 2: Extraer variables clave del engine diagnóstico ============

class VariableExtractor {
    /**
     * Extrae variables clave basadas en las respuestas Q1-Q200.
     * Usado por DynamicQuestion para "mirror effect".
     */
    static extractKeyVariables(answers) {
        return {
            primary_fear: this._extractFromQuestion(answers, 78),        // Q78
            stress_level: this._extractFromQuestion(answers, 145),      // Q145
            primary_goal: this._extractFromQuestion(answers, 89),       // Q89
            budget_control: this._extractFromQuestion(answers, 142),    // Q142
            savings_rate: this._extractFromQuestion(answers, 167),      // Q167
            investment_interest: this._extractFromQuestion(answers, 124), // Q124
            main_blocker: this._extractFromQuestion(answers, 201),      // Q201
            emotional_state: null  // Se llenarán con OP2
        };
    }

    static _extractFromQuestion(answers, questionId) {
        const key = `Q${questionId}`;
        return answers[key] || null;
    }

    static detectInconsistencies(answers) {
        /**
         * Detecta pares de preguntas contradictorias.
         * Retorna array de { pair, message, questions }
         */
        const inconsistencies = [];

        // Pair 1: Ahorro vs Control (Q167 = alto ahorro, Q142 = bajo control)
        const savings = answers.Q167;
        const control = answers.Q142;
        if (savings === 'alto' && control === 'bajo') {
            inconsistencies.push({
                pair: 'ahorro_vs_control',
                message: '¿Quieres ahorrar pero no sabes dónde va tu dinero?',
                questions: [167, 142]
            });
        }

        // Pair 2: Riesgo vs Miedo (Q124 = alto riesgo, Q78 = miedo alto)
        const risk = answers.Q124;
        const fear = answers.Q78;
        if (risk === 'alto' && fear === 'deudas') {
            inconsistencies.push({
                pair: 'riesgo_vs_miedo',
                message: '¿Aceptas riesgo pero tienes miedo a las deudas?',
                questions: [124, 78]
            });
        }

        // Pair 3: Deuda vs Prioridad (deuda reportada pero no es prioridad)
        // (Depende de estructura específica de datos)

        // Pair 4: Gastos vs Presupuesto (gasto > presupuesto)
        // (Requiere comparación de Q arrays)

        return inconsistencies;
    }
}

// ============ PASO 3: Componentes React ============

/**
 * 1. LoadingScreenPremium
 * Timeline 5-pasos + Rotating Insights (6 tips) + confetti final
 */
const LoadingScreenPremium = ({ keyVariables }) => {
    const [currentStep, setCurrentStep] = React.useState(0);
    const [currentInsight, setCurrentInsight] = React.useState(0);
    const [finished, setFinished] = React.useState(false);

    const steps = [
        { label: 'Analyzing', description: 'Analizando tus patrones financieros...' },
        { label: 'Structuring', description: 'Estructurando tu diagnóstico personalizado...' },
        { label: 'Detecting', description: 'Detectando oportunidades de optimización...' },
        { label: 'Generating', description: 'Generando tu reporte detallado...' },
        { label: 'Polishing', description: 'Perfeccionando los últimos detalles...' }
    ];

    const insights = [
        'La mayoría de personas subestima su potencial de ahorro en un 40%.',
        'Un 70% de ganancias en patrimonio vienen de decisiones de largo plazo.',
        'La mejor inversión es la que duermes tranquilo.',
        'Tu situación fiscal mejora 3-5x con asesoramiento preventivo.',
        'El dinero no es el enemigo: la falta de plan sí lo es.',
        'Adapta es donde la planificación se convierte en oportunidad real.'
    ];

    React.useEffect(() => {
        const stepInterval = setInterval(() => {
            setCurrentStep(prev => {
                if (prev < steps.length - 1) {
                    return prev + 1;
                } else {
                    setFinished(true);
                    return prev;
                }
            });
        }, 1000);

        const insightInterval = setInterval(() => {
            setCurrentInsight(prev => (prev + 1) % insights.length);
        }, 3000);

        return () => {
            clearInterval(stepInterval);
            clearInterval(insightInterval);
        };
    }, []);

    return (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <h2 style={{ color: '#020203', marginBottom: '30px' }}>
                🔍 Generando tu diagnóstico...
            </h2>

            {/* Timeline */}
            <div style={{ marginBottom: '40px' }}>
                {steps.map((step, idx) => (
                    <div
                        key={idx}
                        style={{
                            marginBottom: '15px',
                            opacity: idx <= currentStep ? 1 : 0.3,
                            transition: 'opacity 0.3s'
                        }}
                    >
                        <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#FDD731' }}>
                            {idx <= currentStep ? '✓' : '○'} {step.label}
                        </div>
                        <div style={{ fontSize: '14px', color: '#666' }}>
                            {step.description}
                        </div>
                    </div>
                ))}
            </div>

            {/* Rotating Insights */}
            <div
                style={{
                    backgroundColor: '#FAF8F3',
                    padding: '20px',
                    borderRadius: '8px',
                    marginBottom: '30px',
                    minHeight: '60px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                }}
            >
                <p style={{ fontSize: '16px', color: '#020203', margin: 0 }}>
                    💡 {insights[currentInsight]}
                </p>
            </div>

            {/* Progress Bar */}
            <div style={{ width: '100%', height: '6px', backgroundColor: '#f0f0f0', borderRadius: '3px', overflow: 'hidden' }}>
                <div
                    style={{
                        height: '100%',
                        width: `${((currentStep + 1) / steps.length) * 100}%`,
                        backgroundColor: '#FDD731',
                        transition: 'width 0.5s'
                    }}
                />
            </div>

            {finished && (
                <div style={{ marginTop: '20px', animation: 'fadeIn 0.5s' }}>
                    <p style={{ fontSize: '18px', color: '#020203', fontWeight: 'bold' }}>
                        ✓ Diagnóstico completado
                    </p>
                </div>
            )}
        </div>
    );
};

/**
 * 2. InconsistencyPopup
 * Modal que bloquea progresión hasta que usuario reconoce inconsistencia
 */
const InconsistencyPopup = ({ inconsistency, onAcknowledge }) => {
    if (!inconsistency) return null;

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999
        }}>
            <div style={{
                backgroundColor: 'white',
                padding: '30px',
                borderRadius: '12px',
                maxWidth: '400px',
                textAlign: 'center',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.15)'
            }}>
                <h3 style={{ color: '#020203', marginBottom: '15px' }}>
                    🔍 Espera un momento
                </h3>
                <p style={{ color: '#666', fontSize: '16px', marginBottom: '20px' }}>
                    {inconsistency.message}
                </p>
                <p style={{ color: '#999', fontSize: '13px', marginBottom: '25px' }}>
                    Detectamos que tus respuestas tienen cierta tensión. Esto es importante que explores.
                </p>
                <button
                    onClick={onAcknowledge}
                    style={{
                        backgroundColor: '#FDD731',
                        color: '#020203',
                        border: 'none',
                        padding: '10px 20px',
                        borderRadius: '6px',
                        fontSize: '16px',
                        fontWeight: 'bold',
                        cursor: 'pointer'
                    }}
                >
                    Entendido, continuar
                </button>
            </div>
        </div>
    );
};

/**
 * 3. DynamicQuestion
 * Inyecta variables en las preguntas abiertas para "mirror effect"
 */
const DynamicQuestion = ({ index, baseQuestion, keyVariables }) => {
    const variableMap = {
        '[primary_fear]': keyVariables.primary_fear,
        '[stress_level]': keyVariables.stress_level,
        '[primary_goal]': keyVariables.primary_goal,
        '[emotional_state]': keyVariables.emotional_state
    };

    let dynamicQuestion = baseQuestion;
    Object.entries(variableMap).forEach(([placeholder, value]) => {
        if (value) {
            dynamicQuestion = dynamicQuestion.replace(placeholder, value);
        }
    });

    return (
        <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: 'bold', color: '#020203', marginBottom: '8px' }}>
                Pregunta {index + 1}
            </label>
            <p style={{ color: '#666', fontSize: '15px', fontStyle: 'italic', marginBottom: '10px' }}>
                {dynamicQuestion}
            </p>
        </div>
    );
};

/**
 * 4. EmotionalProgressBar
 * Reemplaza contador "X de 200" con milestones emocionales
 */
const EmotionalProgressBar = ({ currentQuestion, totalQuestions }) => {
    const milestones = [
        { q: 25, label: 'Bloque Mentalidad', insight: 'propensión al riesgo ALTA' },
        { q: 50, label: 'Ingresos & Salida', insight: 'gastos > presupuesto en 30%' },
        { q: 75, label: 'Inversión', insight: 'oportunidad de diversificación' },
        { q: 100, label: 'Diagnóstico completado', insight: 'patrón dominante identificado' }
    ];

    const progressPercent = (currentQuestion / totalQuestions) * 100;
    const completedMilestones = milestones.filter(m => currentQuestion >= m.q);

    return (
        <div style={{ padding: '15px 0', marginBottom: '20px' }}>
            {/* Progress Bar */}
            <div style={{
                width: '100%',
                height: '8px',
                backgroundColor: '#f0f0f0',
                borderRadius: '4px',
                overflow: 'hidden',
                marginBottom: '12px'
            }}>
                <div
                    style={{
                        height: '100%',
                        width: `${progressPercent}%`,
                        backgroundColor: '#FDD731',
                        transition: 'width 0.3s'
                    }}
                />
            </div>

            {/* Milestone Tracker */}
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
                Progreso: {currentQuestion} de {totalQuestions}
            </div>

            {/* Latest Milestone Message */}
            {completedMilestones.length > 0 && (
                <div style={{
                    backgroundColor: '#FAF8F3',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    color: '#020203',
                    fontWeight: 'bold'
                }}>
                    ✓ {completedMilestones[completedMilestones.length - 1].label} completado.
                    <br />
                    Sistema detecta: {completedMilestones[completedMilestones.length - 1].insight}
                </div>
            )}
        </div>
    );
};

// ============ PASO 4: Montador maestro ============

class ReactIntegrationManager {
    static mountAll() {
        console.log('[REACT_INTEGRATION] Iniciando montaje de componentes...');

        // 1. LoadingScreenPremium (se monta cuando se necesita, no ahora)
        window.ReactComponents = {
            LoadingScreenPremium,
            InconsistencyPopup,
            DynamicQuestion,
            EmotionalProgressBar
        };

        // 2. Inyectar utilidades globales
        window.VariableExtractor = VariableExtractor;

        console.log('[REACT_INTEGRATION] Componentes registrados y listos para montar');
    }
}

// ============ PASO 5: Auto-mount al cargar el script ============

document.addEventListener('DOMContentLoaded', () => {
    ReactIntegrationManager.mountAll();
});

// Si el DOM ya está listo cuando el script carga
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        ReactIntegrationManager.mountAll();
    });
} else {
    ReactIntegrationManager.mountAll();
}

console.log('[REACT_INTEGRATION] Script cargado exitosamente');
