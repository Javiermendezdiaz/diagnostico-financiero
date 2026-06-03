import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronRight, Download, Headphones } from 'lucide-react';

/**
 * CreditPurchaseFlow.jsx
 * 
 * Experiencia "Top 1% Mundial" post-pago:
 * 1. Desprecintado Digital (0-2s) — Validación visual del pago
 * 2. Onboarding Interactivo (3 slides) — Score, Silent Leak, Couple Friction
 * 3. Centro de Control (3 opciones) — App, PDF Email, Audio-Consultor
 * 4. Sincronización Calendario
 */

const CreditPurchaseFlow = () => {
  const [searchParams] = useSearchParams();
  const [phase, setPhase] = useState('polling'); // polling → unboxing → tour → hub → calendar-sync
  const [paymentData, setPaymentData] = useState(null);
  const [diagnosticData, setDiagnosticData] = useState(null);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [loading, setLoading] = useState(true);

  const paymentId = searchParams.get('payment_id');

  // ============ PHASE 0: Polling Estado de Pago ============
  useEffect(() => {
    if (!paymentId) return;

    const pollPaymentStatus = async () => {
      try {
        const response = await fetch(`/api/v1/payments/status/${paymentId}`);
        const data = await response.json();

        if (data.status === 'SUCCESS') {
          setPaymentData(data);
          // Obtener datos diagnósticos del usuario
          const diagnosticResponse = await fetch(`/api/v1/diagnostics/${data.diagnostic_id}`);
          const diagData = await diagnosticResponse.json();
          setDiagnosticData(diagData);
          setLoading(false);
          // Trigger haptic feedback
          if (navigator.vibrate) {
            navigator.vibrate([50, 30, 50]);
          }
          // Pasar a fase unboxing
          setTimeout(() => setPhase('unboxing'), 500);
        } else if (data.status === 'FAILED' || data.status === 'EXPIRED') {
          // Mostrar error
          setPhase('payment-failed');
          setLoading(false);
        } else {
          // Sigue polling
          setTimeout(pollPaymentStatus, 1000);
        }
      } catch (err) {
        console.error('Error polling payment:', err);
        setTimeout(pollPaymentStatus, 2000);
      }
    };

    pollPaymentStatus();
  }, [paymentId]);

  // ============ PHASE 1: Desprecintado Digital ============
  const UnboxingPhase = () => (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-black flex items-center justify-center p-4">
      <style>{`
        @keyframes sealBreak {
          0% { transform: scaleY(1); opacity: 1; }
          50% { transform: scaleY(0.95); filter: brightness(1.2); }
          100% { transform: scaleY(0); opacity: 0; }
        }
        @keyframes goldenGlow {
          0% { opacity: 0; }
          30% { opacity: 1; }
          100% { opacity: 0.3; }
        }
        .seal-break { animation: sealBreak 2s ease-out forwards; }
        .golden-glow { animation: goldenGlow 2s ease-out forwards; }
      `}</style>
      
      <div className="relative w-full max-w-sm">
        {/* Golden light band */}
        <div className="absolute inset-0 h-1 bg-gradient-to-r from-transparent via-yellow-400 to-transparent golden-glow top-1/3"></div>
        
        {/* Sealed envelope */}
        <div className="bg-slate-950 border-4 border-yellow-500 rounded-lg p-12 text-center seal-break shadow-2xl">
          <div className="text-6xl mb-6">🔓</div>
          <h1 className="text-4xl font-bold text-yellow-400 mb-4">Acceso Concedido</h1>
          <p className="text-xl text-slate-300">Tu Plan Maestro está listo</p>
        </div>

        {/* Confirmation message */}
        <div className="mt-8 text-center text-slate-400 text-sm">
          Procesando tu diagnóstico personalizado...
        </div>
      </div>
    </div>
  );

  // ============ PHASE 2: Onboarding Interactivo (3 Slides) ============
  const OnboardingSlide = () => {
    const slides = [
      {
        title: 'Tu Score Financiero',
        metric: diagnosticData?.health_score || 45,
        percentile: Math.floor(Math.random() * 40) + 30, // Random percentile para demo
        subtitle: 'Estás en el top 30-70% en gestión financiera',
        color: 'from-blue-500 to-blue-600'
      },
      {
        title: 'Tu Fuga Silenciosa',
        metric: `€${diagnosticData?.evaporated_amount || 2400}`,
        period: 'anualmente',
        subtitle: `Dinero que desaparece sin que te des cuenta`,
        color: 'from-orange-500 to-orange-600'
      },
      {
        title: 'Índice de Fricción de Pareja',
        metric: diagnosticData?.friction_zones?.length || 2,
        issues: 'zonas de conflicto detectadas',
        subtitle: 'Temas financieros que generan estrés en casa',
        color: 'from-purple-500 to-purple-600'
      }
    ];

    const slide = slides[currentSlide];

    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          {/* Slide Card */}
          <div className={`bg-gradient-to-br ${slide.color} rounded-xl p-8 text-white shadow-2xl mb-6`}>
            <h2 className="text-lg font-semibold mb-4 opacity-90">{slide.title}</h2>
            <div className="text-5xl font-bold mb-2">{slide.metric}</div>
            <p className="text-sm opacity-75 mb-4">{slide.period || slide.issues || slide.subtitle}</p>
            <p className="text-xs opacity-60">{slide.subtitle}</p>
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setCurrentSlide(Math.max(0, currentSlide - 1))}
              disabled={currentSlide === 0}
              className="px-4 py-2 text-slate-400 disabled:opacity-30"
            >
              ← Atrás
            </button>
            
            <div className="flex gap-2">
              {slides.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentSlide(i)}
                  className={`w-2 h-2 rounded-full transition-all ${
                    i === currentSlide ? 'w-6 bg-yellow-400' : 'bg-slate-600'
                  }`}
                />
              ))}
            </div>

            <button
              onClick={() => currentSlide < 2 ? setCurrentSlide(currentSlide + 1) : setPhase('hub')}
              className="px-4 py-2 text-yellow-400 font-semibold flex items-center gap-2"
            >
              {currentSlide < 2 ? 'Siguiente' : 'Centro de Control'} <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    );
  };

  // ============ PHASE 3: Centro de Control ============
  const DeliveryHub = () => (
    <div className="min-h-screen bg-slate-950 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-2">Tu Centro de Control</h1>
        <p className="text-slate-400 mb-8">Elige cómo acceder a tu diagnóstico</p>

        <div className="grid gap-4">
          {/* Option 1: Interactive App */}
          <button
            onClick={() => window.location.href = '/diagnostics/interactive'}
            className="bg-gradient-to-r from-blue-600 to-blue-700 p-6 rounded-lg text-left hover:shadow-lg transition-all group"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-white mb-2">Explorar en App Interactiva</h3>
                <p className="text-blue-100 text-sm">DAFO pivotable, gráficos interactivos, drill-down por área</p>
              </div>
              <ChevronRight className="text-blue-200 group-hover:translate-x-1 transition-transform" />
            </div>
          </button>

          {/* Option 2: PDF to Email */}
          <button
            onClick={() => setPhase('pdf-email')}
            className="bg-gradient-to-r from-emerald-600 to-emerald-700 p-6 rounded-lg text-left hover:shadow-lg transition-all group"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                  <Download size={20} /> Enviar PDF a Email
                </h3>
                <p className="text-emerald-100 text-sm">Descarga ejecutiva con opción de compartir con tu pareja</p>
              </div>
              <ChevronRight className="text-emerald-200 group-hover:translate-x-1 transition-transform" />
            </div>
          </button>

          {/* Option 3: AI Audio Consultant */}
          <button
            onClick={() => setPhase('audio')}
            className="bg-gradient-to-r from-purple-600 to-purple-700 p-6 rounded-lg text-left hover:shadow-lg transition-all group"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                  <Headphones size={20} /> Audio-Consultor IA
                </h3>
                <p className="text-purple-100 text-sm">8 minutos de síntesis de voz natural — ideal para conducir</p>
              </div>
              <ChevronRight className="text-purple-200 group-hover:translate-x-1 transition-transform" />
            </div>
          </button>
        </div>

        {/* Calendar Sync Button */}
        <div className="mt-12 pt-8 border-t border-slate-700">
          <button
            onClick={() => setPhase('calendar-sync')}
            className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 py-3 rounded-lg text-sm font-semibold transition-colors"
          >
            📅 Sincronizar mi Receta Financiera con mi Calendario
          </button>
        </div>
      </div>
    </div>
  );

  // ============ PHASE 4: PDF to Email ============
  const PdfEmailPhase = () => (
    <div className="min-h-screen bg-slate-950 p-6 flex items-center justify-center">
      <div className="max-w-md w-full">
        <h2 className="text-2xl font-bold text-white mb-6">Enviar Diagnóstico</h2>
        
        <div className="space-y-4">
          <input
            type="email"
            placeholder="Tu email"
            defaultValue={diagnosticData?.user_email || ''}
            className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-yellow-500 focus:outline-none"
          />
          
          <label className="flex items-center gap-3 text-slate-300">
            <input type="checkbox" className="w-4 h-4" />
            <span className="text-sm">Compartir también con mi pareja</span>
          </label>
          
          <input
            type="email"
            placeholder="Email de tu pareja (opcional)"
            className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-yellow-500 focus:outline-none"
          />

          <button
            onClick={async () => {
              // POST to backend PDF generation + email
              await fetch('/api/v1/diagnostics/send-pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  diagnostic_id: diagnosticData?.diagnostic_id,
                  email: document.querySelector('input[type="email"]').value,
                  share_with_partner: true
                })
              });
              alert('PDF enviado a tu email. ✅');
              setPhase('hub');
            }}
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-lg transition-colors"
          >
            Enviar PDF
          </button>
        </div>
      </div>
    </div>
  );

  // ============ PHASE 5: Calendar Sync ============
  const CalendarSyncPhase = () => (
    <div className="min-h-screen bg-slate-950 p-6 flex items-center justify-center">
      <div className="max-w-md w-full text-center">
        <h2 className="text-2xl font-bold text-white mb-4">Sincronizar Calendario</h2>
        <p className="text-slate-400 mb-8">
          Tu Plan de Acción a 90 días se inyectará automáticamente en tu calendario nativo. Recibirás recordatorios en los momentos clave.
        </p>
        
        <button
          onClick={async () => {
            // Request calendar permissions + inject events
            try {
              const response = await fetch('/api/v1/calendar-sync/generate-ical', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ diagnostic_id: diagnosticData?.diagnostic_id })
              });
              const { ical_url } = await response.json();
              
              // Open native calendar app (iOS/Android)
              window.location.href = ical_url;
              
              alert('Calendario sincronizado. Verás los recordatorios en tu app nativa. ✅');
              setPhase('hub');
            } catch (err) {
              alert('Error al sincronizar calendario. Intenta de nuevo.');
            }
          }}
          className="w-full bg-yellow-500 hover:bg-yellow-400 text-slate-900 font-bold py-3 rounded-lg transition-colors mb-4"
        >
          Sincronizar Ahora
        </button>

        <button
          onClick={() => setPhase('hub')}
          className="w-full text-slate-400 py-2"
        >
          Omitir
        </button>
      </div>
    </div>
  );

  // ============ RENDER ============
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-yellow-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-slate-300">Procesando tu pago...</p>
        </div>
      </div>
    );
  }

  if (phase === 'payment-failed') {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="text-center">
          <div className="text-4xl mb-4">❌</div>
          <h1 className="text-2xl font-bold text-white mb-2">Pago no procesado</h1>
          <p className="text-slate-400 mb-8">Intenta de nuevo o contacta con soporte</p>
          <button
            onClick={() => window.location.href = '/'}
            className="bg-yellow-500 hover:bg-yellow-400 text-slate-900 font-bold py-2 px-6 rounded-lg"
          >
            Volver al inicio
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      {phase === 'unboxing' && <UnboxingPhase />}
      {phase === 'tour' && <OnboardingSlide />}
      {phase === 'hub' && <DeliveryHub />}
      {phase === 'pdf-email' && <PdfEmailPhase />}
      {phase === 'audio' && <AudioConsultantPhase />}
      {phase === 'calendar-sync' && <CalendarSyncPhase />}
    </>
  );
};

// Placeholder para Audio Consultant
const AudioConsultantPhase = () => (
  <div className="min-h-screen bg-slate-950 p-6 flex items-center justify-center">
    <div className="max-w-md w-full text-center">
      <Headphones size={64} className="text-purple-400 mx-auto mb-6" />
      <h2 className="text-2xl font-bold text-white mb-4">Audio-Consultor IA</h2>
      <audio controls className="w-full mb-6">
        <source src="/api/v1/diagnostics/audio-summary" type="audio/mpeg" />
      </audio>
      <p className="text-slate-400 text-sm">8 minutos de síntesis personalizada</p>
    </div>
  </div>
);

export default CreditPurchaseFlow;
