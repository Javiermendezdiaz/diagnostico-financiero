#!/usr/bin/env node
/**
 * ESPEJO FANTASMA - Complete Technical Architecture Document
 * Couple Mirror (Mapa de Fricción Conyugal) for Diagnóstico Financiero
 *
 * Generates comprehensive technical design in Word format
 */

const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, PageBreak,
        AlignmentType, WidthType, BorderStyle, ShadingType, HeadingLevel, VerticalAlign,
        LevelFormat, PageOrientation } = require('docx');
const fs = require('fs');
const path = require('path');

// Color scheme
const COLORS = {
  primary: "1a1a1a",      // Negro Adapta
  accent: "FFB81C",        // Amarillo Adapta
  green: "388E3C",         // Verde alineados
  yellow: "FBC02D",        // Amarillo divergencia suave
  red: "D32F2F",           // Rojo agujeros negros
  lightBg: "F5F5F5",       // Fondo claro
  border: "CCCCCC",        // Borde gris
  text: "333333"           // Texto oscuro
};

function createBorder(color = COLORS.border, size = 1) {
  return { style: BorderStyle.SINGLE, size, color };
}

function createTable(colWidths, rows, fullWidth = 9360) {
  const borders = {
    top: createBorder(),
    bottom: createBorder(),
    left: createBorder(),
    right: createBorder(),
    insideHorizontal: createBorder(),
    insideVertical: createBorder()
  };

  const tableRows = rows.map((rowData, idx) => {
    const cells = rowData.map((cellData, cellIdx) => {
      const isHeader = idx === 0;
      const bgColor = isHeader ? COLORS.accent : (idx % 2 === 0 ? COLORS.lightBg : "FFFFFF");

      return new TableCell({
        borders,
        width: { size: colWidths[cellIdx], type: WidthType.DXA },
        shading: { fill: bgColor, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 100, left: 120, right: 120 },
        verticalAlign: VerticalAlign.CENTER,
        children: Array.isArray(cellData) ? cellData : [
          new Paragraph({
            children: [new TextRun({
              text: cellData || "",
              bold: isHeader,
              color: isHeader ? "FFFFFF" : COLORS.text,
              size: isHeader ? 24 : 22
            })],
            alignment: isHeader ? AlignmentType.CENTER : AlignmentType.LEFT
          })
        ]
      });
    });

    return new TableRow({ children: cells });
  });

  return new Table({
    width: { size: fullWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: tableRows
  });
}

function createHeading(text, level = 1) {
  const sizes = { 1: 32, 2: 28, 3: 24 };
  const spacing = { 1: { before: 300, after: 200 }, 2: { before: 200, after: 150 }, 3: { before: 150, after: 100 } };

  return new Paragraph({
    heading: level === 1 ? HeadingLevel.HEADING_1 : level === 2 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3,
    children: [new TextRun({ text, bold: true, size: sizes[level], color: COLORS.primary })],
    spacing: spacing[level],
    border: level === 1 ? { bottom: { style: BorderStyle.SINGLE, size: 6, color: COLORS.accent, space: 1 } } : undefined
  });
}

function createBodyParagraph(text, indent = 0) {
  return new Paragraph({
    children: [new TextRun({ text, size: 22, color: COLORS.text })],
    spacing: { line: 360, after: 120 },
    indent: { left: indent > 0 ? 360 : 0 }
  });
}

function createBulletPoint(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    children: [new TextRun({ text, size: 22, color: COLORS.text })],
    spacing: { after: 60 }
  });
}

function createCodeBlock(code) {
  const lines = code.split('\n');
  const children = [];

  lines.forEach((line, idx) => {
    if (idx > 0) children.push(new TextRun("\n"));
    children.push(new TextRun({
      text: line,
      font: "Courier New",
      size: 20,
      color: "555555"
    }));
  });

  return new Paragraph({
    children,
    border: { left: { style: BorderStyle.SINGLE, size: 3, color: COLORS.accent } },
    shading: { fill: "F9F9F9", type: ShadingType.CLEAR },
    indent: { left: 360 },
    spacing: { line: 240, before: 120, after: 120 }
  });
}

// Main document
const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1440, hanging: 360 } } } }
        ]
      },
      {
        reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } }
        ]
      }
    ]
  },
  styles: {
    default: {
      document: {
        run: { font: "Arial", size: 22 },
        paragraph: { spacing: { line: 360 } }
      }
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: COLORS.primary },
        paragraph: { spacing: { before: 300, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: COLORS.primary },
        paragraph: { spacing: { before: 200, after: 150 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: COLORS.primary },
        paragraph: { spacing: { before: 150, after: 100 }, outlineLevel: 2 } }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: {
          width: 12240,   // US Letter
          height: 15840,
          orientation: PageOrientation.PORTRAIT
        },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [
      // TITLE PAGE
      new Paragraph({
        children: [new TextRun({
          text: "ESPEJO FANTASMA",
          bold: true,
          size: 48,
          color: COLORS.primary
        })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 1800, after: 300 }
      }),
      new Paragraph({
        children: [new TextRun({
          text: "Mapa de Fricción Conyugal",
          size: 32,
          color: COLORS.accent,
          bold: true
        })],
        alignment: AlignmentType.CENTER,
        spacing: { after: 600 }
      }),
      new Paragraph({
        children: [new TextRun({
          text: "Arquitectura Técnica Completa para Diagnóstico Financiero",
          size: 24,
          color: COLORS.text,
          italics: true
        })],
        alignment: AlignmentType.CENTER,
        spacing: { after: 1200 }
      }),
      new Paragraph({
        children: [new TextRun({
          text: "Versión: 1.0\nFecha: Junio 2026\nEstate: DISEÑO ARQUITECTÓNICO\nEsfuerzo Estimado MVP: 80-100 horas",
          size: 22,
          color: COLORS.text
        })],
        alignment: AlignmentType.CENTER,
        spacing: { after: 1800 }
      }),
      new Paragraph({ children: [new PageBreak()] }),

      // SECTION 1: RESOLVIENDO PREGUNTAS CRÍTICAS
      createHeading("1. Resolución de Preguntas Críticas"),
      new Paragraph({
        children: [new TextRun({
          text: "Antes de proceder con la arquitectura, se responden las 5 preguntas estratégicas que definen el alcance:",
          size: 22,
          color: COLORS.text,
          italics: true
        })],
        spacing: { after: 200 }
      }),

      new Paragraph({
        children: [new TextRun({
          text: "1. ¿Cuántas preguntas de 'Familia y Dinero' son?",
          bold: true,
          size: 22,
          color: COLORS.primary
        })],
        spacing: { after: 100 }
      }),
      createBodyParagraph("El schema actual de 500 preguntas organizado en 10 capas no tiene una sección explícita llamada 'Familia y Dinero'. Sin embargo, existen ~35-40 preguntas distribuidas en VARIAS capas que abordan dinámicas conyugales:"),
      createBulletPoint("Burnout (pregunta #4): '¿Discutes dinero frecuentemente con tu pareja/familia de forma tensa?'"),
      createBulletPoint("Estrés (pregunta #47): '¿Sacrificas sueño, ejercicio o relaciones por dinero/trabajo?'"),
      createBulletPoint("Secretos (pregunta #13): '¿Compartir dinero con pareja/familia causa conflicto?'"),
      createBulletPoint("Herencia (múltiples): Visión de lujo, deuda compartida, transparencia financiera"),
      createBodyParagraph("DECISIÓN ARQUITECTÓNICA: Crear una NUEVA capa denominada 'Familia y Dinero' con 50 preguntas enfocadas 100% en dinámicas conyugales. Esto es más limpio que fragmentar en múltiples capas."),

      new Paragraph({
        children: [new TextRun({
          text: "2. ¿Email para invitar pareja o solo link + WhatsApp?",
          bold: true,
          size: 22,
          color: COLORS.primary
        })],
        spacing: { before: 200, after: 100 }
      }),
      createBodyParagraph("RECOMENDACIÓN: Ambos. El sistema genera un magic link único que se puede:"),
      createBulletPoint("Copiar y compartir vía WhatsApp (más rápido, más casual)"),
      createBulletPoint("Enviar vía email automático (más profesional, registro de auditoría)"),
      createBodyParagraph("El link de invitación es el mecanismo principal; email es una capa de conveniencia adicional."),

      new Paragraph({
        children: [new TextRun({
          text: "3. ¿Cuándo se muestra el Mapa? (Durante test de pareja o solo después?)",
          bold: true,
          size: 22,
          color: COLORS.primary
        })],
        spacing: { before: 200, after: 100 }
      }),
      createBodyParagraph("DECISIÓN: Sólo DESPUÉS. El flujo es:"),
      createBulletPoint("Usuario 1 completa test completo → PDF individual"),
      createBulletPoint("Usuario 1 invita pareja → Pareja completa solo 'Familia y Dinero' (blind mode)"),
      createBulletPoint("Pareja completa → Se desbloquea 'Ver Mapa de Fricción' en ambos PDFs"),
      createBodyParagraph("Mostrar el Mapa durante el test contaminaría las respuestas. El 'aha moment' sucede después en un PDF nuevo o sección adicional."),

      new Paragraph({
        children: [new TextRun({
          text: "4. ¿Puede una pareja 'desacoplarse' después?",
          bold: true,
          size: 22,
          color: COLORS.primary
        })],
        spacing: { before: 200, after: 100 }
      }),
      createBodyParagraph("DECISIÓN: SÍ, pero con restricciones. La tabla couple_links permite un estado 'decoupled_at' (timestamp). Esto:"),
      createBulletPoint("Mantiene auditoría histórica (RGPD compliance)"),
      createBulletPoint("Permite que Usuario 1 invite a otra pareja después"),
      createBulletPoint("Bloquea re-invitaciones al mismo email (validación deduplication)"),
      createBulletPoint("No borra datos históricos; solo marca como inactivo"),

      new Paragraph({
        children: [new TextRun({
          text: "5. ¿Cuál es el CTA específico después de ver el Mapa?",
          bold: true,
          size: 22,
          color: COLORS.primary
        })],
        spacing: { before: 200, after: 100 }
      }),
      createBodyParagraph("RECOMENDACIÓN: Múltiples CTAs contextuales basados en tipo de fricción detectada:"),
      createBulletPoint("ALINEADOS (Verde): 'Excelente comunicación. Próximo paso: Planificación conjunta. Reserva sesión de pareja' → CTA: Calendly link"),
      createBulletPoint("DIVERGENCIA SUAVE (Amarillo): 'Pequeñas diferencias. Recomendación: Taller 'Dinero sin Conflicto' para parejas' → CTA: Landing taller"),
      createBulletPoint("AGUJEROS NEGROS (Rojo): 'Desacuerdo significativo. Recomendación: Sesión de mediación financiera' → CTA: Booking consultoría especializada"),
      createBodyParagraph("El Mapa mismo es el CTA: el 'aha moment' de ver juntos genera urgencia de actuar."),

      new Paragraph({ children: [new PageBreak()] }),

      // SECTION 2: UX FLOW
      createHeading("2. Flujo UX: Paso a Paso"),

      createHeading("2.1 Flujo del Usuario 1 (Invitador)", 2),
      createBulletPoint("Completa cuestionario de 500 preguntas"),
      createBulletPoint("Llega a pantalla 'Resultados' con su PDF generado"),
      createBulletPoint("Ve nueva sección: 'Familia y Dinero: ¿Tienes pareja?'"),
      createBulletPoint("Si elige 'SÍ': Botón 'Invitar Pareja a Diagnóstico' (prominente, color accent)"),
      createBulletPoint("Sistema genera magic link único → copia a portapapeles"),
      createBulletPoint("Instrucciones: 'Envía este link a tu pareja por WhatsApp o email. Tardará ~8 minutos'"),
      createBulletPoint("Usuario 1 puede compartir, esperar o cerrar (no bloquea su PDF)"),

      createHeading("2.2 Flujo del Usuario 2 (Invitado)", 2),
      createBulletPoint("Recibe link: https://diagnostico.adapta.com/couple/abc123xyz"),
      createBulletPoint("Landing minimalista: 'Tu pareja te invitó a responder 50 preguntas sobre dinero'"),
      createBulletPoint("Signup ultra-rápido: Email + Nombre (validar email ≠ Usuario 1)"),
      createBulletPoint("Botón: 'Responder preguntas' → Entra a modo 'Blind' (blind_test_id generado)"),
      createBulletPoint("Responde SÓLO 50 preguntas de 'Familia y Dinero' (no las 500)"),
      createBulletPoint("Sin acceso a respuestas de Usuario 1 (anónimas temporales)"),
      createBulletPoint("Al terminar: 'Listo! Tu pareja verá el Mapa en 24 horas. Te enviaremos un link privado'"),

      createHeading("2.3 Generación del Mapa de Fricción (Backend)", 2),
      createBulletPoint("Trigger: POST /api/couple/analyze after Usuario 2 completes"),
      createBulletPoint("IA compara puntajes tema-por-tema (ahorro, deuda, riesgo, inversión, consumo)"),
      createBulletPoint("Calcula divergencia: cosine similarity entre vectores de respuestas"),
      createBulletPoint("Clasifica 3 zonas:"),
      new Paragraph({
        numbering: { reference: "bullets", level: 1 },
        children: [new TextRun("ALINEADOS (diff < 15%): Verde ✓")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 1 },
        children: [new TextRun("DIVERGENCIA SUAVE (15-40%): Amarillo ⚠")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 1 },
        children: [new TextRun("AGUJEROS NEGROS (> 40%): Rojo ✗")]
      }),
      createBulletPoint("Genera JSON + PDF con gráfica interactiva"),
      createBulletPoint("Envía email a ambos: 'Tu Mapa está listo. Abre tu PDF actualizado'"),

      createHeading("2.4 Visualización del Mapa", 2),
      createBulletPoint("Ambos usuarios ven el Mapa en una nueva página (página 3+) de su PDF individual"),
      createBulletPoint("Gráfica interactiva: 3 cuadrantes con % por cada zona"),
      createBulletPoint("Heatmap de tópicos específicos: (Ahorro, Deuda, Riesgo, Inversión, Consumo)"),
      createBulletPoint("Insights en lenguaje natural: 'Ambos quieren ahorrar, pero están 60% en desacuerdo sobre destino'"),
      createBulletPoint("CTA contextual según color → Reserva sesión, compra taller, etc."),

      new Paragraph({ children: [new PageBreak()] }),

      // SECTION 3: DATABASE SCHEMA
      createHeading("3. Schema de Base de Datos (SQL)"),

      createHeading("3.1 Tablas Nuevas", 2),
      createBodyParagraph("Tres tablas nuevas requieren agregar la funcionalidad de pareja:"),

      createHeading("Tabla: couple_links", 3),
      createCodeBlock(`CREATE TABLE couple_links (
  coupling_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user1_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  user2_id UUID NULLABLE REFERENCES users(id) ON DELETE CASCADE,
  link_token VARCHAR(256) UNIQUE NOT NULL,  -- magic link token
  link_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  link_expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '7 days',
  completed_at TIMESTAMP NULLABLE,  -- when user2 submits
  decoupled_at TIMESTAMP NULLABLE,  -- when uncoupled
  status ENUM('pending', 'active', 'decoupled', 'expired') DEFAULT 'pending',
  invitation_method ENUM('link', 'email', 'both') DEFAULT 'link',
  invitation_email VARCHAR(255) NULLABLE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_couple_links_user1 ON couple_links(user1_id);
CREATE INDEX idx_couple_links_user2 ON couple_links(user2_id);
CREATE INDEX idx_couple_links_token ON couple_links(link_token);
CREATE INDEX idx_couple_links_status ON couple_links(status);`),

      createHeading("Tabla: couple_responses", 3),
      createCodeBlock(`CREATE TABLE couple_responses (
  response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coupling_id UUID NOT NULL REFERENCES couple_links(coupling_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  question_id VARCHAR(50) NOT NULL,  -- e.g., "familia_001"
  question_topic VARCHAR(50),  -- e.g., "ahorro", "deuda", "riesgo"
  score_numeric INT CHECK (score_numeric BETWEEN 0 AND 100),
  response_text VARCHAR(500) NULLABLE,
  blind_response_id VARCHAR(256),  -- anonymous temp ID for blind mode
  is_blind BOOLEAN DEFAULT TRUE,
  answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_couple_responses_coupling ON couple_responses(coupling_id);
CREATE INDEX idx_couple_responses_user ON couple_responses(user_id);
CREATE INDEX idx_couple_responses_question ON couple_responses(question_id);`),

      createHeading("Tabla: couple_analysis_results", 3),
      createCodeBlock(`CREATE TABLE couple_analysis_results (
  analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coupling_id UUID NOT NULL REFERENCES couple_links(coupling_id) ON DELETE CASCADE,
  analysis_type ENUM('similarity_scores', 'friction_map', 'insights') DEFAULT 'friction_map',
  overall_similarity NUMERIC(5,2),  -- 0-100% (100 = perfect alignment)
  topic_similarities JSONB,  -- {"ahorro": 85, "deuda": 45, ...}
  friction_zones JSONB,  -- {"aligned": [...], "divergence_soft": [...], "black_holes": [...]}
  friction_heatmap_data JSONB,  -- for chart generation
  ai_insights_es TEXT,  -- Spanish insights
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  pdf_path VARCHAR(500) NULLABLE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analysis_coupling ON couple_analysis_results(coupling_id);`),

      createHeading("3.2 Modificación a Tabla Existente: users", 3),
      createCodeBlock(`ALTER TABLE users ADD COLUMN (
  partner_id UUID NULLABLE REFERENCES users(id) ON DELETE SET NULL,
  couple_relationship_status ENUM('single', 'coupled', 'decoupled') DEFAULT 'single',
  is_invitation_recipient BOOLEAN DEFAULT FALSE,
  invitation_accepted_at TIMESTAMP NULLABLE
);

CREATE INDEX idx_users_partner ON users(partner_id);`),

      new Paragraph({ children: [new PageBreak()] }),

      // SECTION 4: API ENDPOINTS
      createHeading("4. Endpoints API"),

      createHeading("4.1 POST /api/couple/invite-partner", 2),
      createBodyParagraph("Usuario 1 invita a pareja. Genera magic link y envía email (opcional)."),
      createCodeBlock(`REQUEST:
{
  "user_id": "uuid-user1",
  "partner_email": "partner@example.com",
  "invitation_method": "both",  // link | email | both
  "send_email": true
}

RESPONSE (201):
{
  "coupling_id": "uuid-coupling-123",
  "link_token": "abc123xyz789",
  "invitation_url": "https://diagnostico.adapta.com/couple/abc123xyz789",
  "link_expires_at": "2026-06-08T12:00:00Z",
  "message": "Link generado. Válido por 7 días."
}`),

      createHeading("4.2 GET /api/couple/{link_token}", 2),
      createBodyParagraph("Landing minimalista para pareja. Retorna info básica de invitación."),
      createCodeBlock(`REQUEST:
GET /api/couple/abc123xyz789

RESPONSE (200):
{
  "coupling_id": "uuid-coupling-123",
  "inviter_name": "Juan",
  "invitation_expires_at": "2026-06-08T12:00:00Z",
  "status": "pending",
  "message": "Juan te invitó a responder 50 preguntas sobre dinero en pareja"
}

// Si token expirado o inválido:
RESPONSE (410):
{
  "error": "Link expirado o inválido. Solicita uno nuevo a tu pareja.",
  "expired": true
}`),

      createHeading("4.3 POST /api/couple/signup-and-start-test", 2),
      createBodyParagraph("Usuario 2 se registra (ultra-rápido) y comienza test blind."),
      createCodeBlock(`REQUEST:
{
  "link_token": "abc123xyz789",
  "email": "partner@example.com",
  "nombre": "María",
  "accept_terms": true
}

RESPONSE (201):
{
  "user_id": "uuid-user2-new",
  "blind_test_id": "blind-test-xyz",
  "coupling_id": "uuid-coupling-123",
  "message": "Registrado. Comienza el test...",
  "questions_count": 50,
  "estimated_time_minutes": 8
}`),

      createHeading("4.4 POST /api/couple/answers", 2),
      createBodyParagraph("Pareja envía respuestas individuales (una por una o bulk). Blind mode."),
      createCodeBlock(`REQUEST:
{
  "user_id": "uuid-user2",
  "coupling_id": "uuid-coupling-123",
  "blind_test_id": "blind-test-xyz",
  "answers": [
    {
      "question_id": "familia_001",
      "question_topic": "ahorro",
      "score_numeric": 75,
      "response_text": "Quiero ahorrar al menos 30% mensual"
    },
    ...
  ]
}

RESPONSE (200):
{
  "answers_saved": 50,
  "test_complete": true,
  "message": "Respuestas guardadas. Mapa será generado en 24 horas."
}`),

      createHeading("4.5 POST /api/couple/analyze", 2),
      createBodyParagraph("Backend: Análisis IA + generación de Mapa. Trigger automático o manual."),
      createCodeBlock(`REQUEST (internal/admin):
{
  "coupling_id": "uuid-coupling-123"
}

RESPONSE (200):
{
  "analysis_id": "uuid-analysis",
  "overall_similarity": 62.5,
  "topic_similarities": {
    "ahorro": 85,
    "deuda": 45,
    "riesgo": 70,
    "inversión": 55,
    "consumo": 80
  },
  "friction_zones": {
    "aligned": ["ahorro", "consumo"],
    "divergence_soft": ["riesgo", "inversión"],
    "black_holes": ["deuda"]
  },
  "ai_insights": "Ambos priorizan ahorros, pero tienen visiones opuestas sobre deuda...",
  "pdf_generated": true,
  "emails_sent": true
}`),

      createHeading("4.6 GET /api/couple/results/{coupling_id}", 2),
      createBodyParagraph("Retorna Mapa completo (JSON + PDF path) para visualización."),
      createCodeBlock(`REQUEST:
GET /api/couple/results/uuid-coupling-123?user_id=uuid-user1

RESPONSE (200):
{
  "analysis_id": "uuid-analysis",
  "overall_similarity": 62.5,
  "topic_similarities": { ... },
  "friction_zones": { ... },
  "ai_insights_es": "...",
  "friction_heatmap_data": { ... },
  "pdf_path": "/reports/couple-map-uuid-analysis.pdf",
  "generated_at": "2026-06-01T14:22:00Z",
  "can_view": true  // Validar que user pertenezca a coupling
}`),

      createHeading("4.7 POST /api/couple/decouple", 2),
      createBodyParagraph("Usuario desvincula pareja (soft delete, no borra datos)."),
      createCodeBlock(`REQUEST:
{
  "coupling_id": "uuid-coupling-123",
  "user_id": "uuid-user1"
}

RESPONSE (200):
{
  "message": "Pareja desvinculada. Puedes invitar a otra.",
  "decoupled_at": "2026-06-01T14:25:00Z"
}`),

      new Paragraph({ children: [new PageBreak()] }),

      // SECTION 5: FRICTION ALGORITHM
      createHeading("5. Algoritmo de Fricción Conyugal"),

      createHeading("5.1 Conceptos", 2),
      createBodyParagraph("El Mapa cuantifica 'agujeros negros' en la comunicación financiera usando 3 métodos combinados:"),

      createHeading("Método 1: Cosine Similarity (Similitud de Vectores)", 3),
      createBodyParagraph("Cada usuario es un vector de 50 dimensiones (una por pregunta). Se calcula similitud coseno:"),
      createCodeBlock(`similarity = (V1 · V2) / (||V1|| × ||V2||)
donde:
  V1 = vector de respuestas Usuario 1
  V2 = vector de respuestas Usuario 2

Resultado: 0 (opuestos) a 1 (idénticos) → Convertir a % (0-100)`),

      createHeading("Método 2: Divergencia por Tema", 3),
      createBodyParagraph("Agrupar preguntas por tema (ahorro, deuda, riesgo, inversión, consumo) y calcular divergencia euclidiana en cada tema:"),
      createCodeBlock(`divergencia_tema = sqrt(sum((V1[i] - V2[i])^2)) / 50
Clasificación:
  < 15 puntos → ALINEADO (verde)
  15-40 puntos → DIVERGENCIA SUAVE (amarillo)
  > 40 puntos → AGUJERO NEGRO (rojo)`),

      createHeading("Método 3: Detección de Contradicciones Explícitas", 3),
      createBodyParagraph("Preguntas pareadas (Ej: Usuario 1 'quiero ahorrar 30%' vs Usuario 2 'queremos gastar en viajes'). Detectar desacuerdo directo:"),
      createCodeBlock(`if pregunta_pareada:
  if abs(respuesta_u1 - respuesta_u2) > threshold (60 puntos):
    marcar como BLACK_HOLE
    generar insight: "Desacuerdo sobre [tema]"`),

      createHeading("5.2 Pseudocódigo del Algoritmo Completo", 2),
      createCodeBlock(`FUNCTION analyze_couple_friction(coupling_id):
  u1_responses = get_responses(coupling_id, user1_id)
  u2_responses = get_responses(coupling_id, user2_id)

  // Build vectors
  vector_u1 = [u1_responses[q] for q in all_questions]
  vector_u2 = [u2_responses[q] for q in all_questions]

  // Overall similarity (cosine)
  overall_similarity = cosine_similarity(vector_u1, vector_u2) * 100

  // Per-topic similarity
  topic_similarities = {}
  for topic in [ahorro, deuda, riesgo, inversion, consumo]:
    topic_u1 = [u1_responses[q] for q in questions_by_topic[topic]]
    topic_u2 = [u2_responses[q] for q in questions_by_topic[topic]]
    topic_similarities[topic] = cosine_similarity(topic_u1, topic_u2) * 100

  // Classify zones
  friction_zones = {
    aligned: [],
    divergence_soft: [],
    black_holes: []
  }

  for topic, similarity in topic_similarities:
    if similarity > 85:
      friction_zones['aligned'].append(topic)
    elif similarity >= 60:
      friction_zones['divergence_soft'].append(topic)
    else:
      friction_zones['black_holes'].append(topic)

  // Generate heatmap data
  heatmap = {
    topic: similarity for topic, similarity in topic_similarities
  }

  // Generate AI insights
  insights = generate_insights(
    overall_similarity,
    topic_similarities,
    friction_zones,
    paired_question_analysis()
  )

  // Save results
  save_analysis(coupling_id, {
    overall_similarity,
    topic_similarities,
    friction_zones,
    heatmap,
    insights
  })

  // Generate PDF
  generate_couple_map_pdf(coupling_id)

  // Send emails
  send_email_to_both_users(coupling_id)

  return {success: true, analysis_id, ...}
END FUNCTION`),

      createHeading("5.3 Umbrales de Clasificación", 2),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("ALINEADOS (Verde): Similitud > 85% → Entienden dinero de forma similar, pocos conflictos")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("DIVERGENCIA SUAVE (Amarillo): 60-85% → Diferencias pequeñas, manejables con comunicación")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("AGUJEROS NEGROS (Rojo): < 60% → Desacuerdos profundos, requieren mediación")]
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // SECTION 6: PDF INTEGRATION
      createHeading("6. Integración PDF"),

      createHeading("6.1 Estructura del PDF Actualizado", 2),
      createBodyParagraph("El PDF de Usuario 1 y Usuario 2 incluirá nuevas secciones cuando estén acoplados:"),
      createBulletPoint("Página 1-2: Resultados diagnóstico individual (existente)"),
      createBulletPoint("Página 3: [NUEVO si acoplado] Sección 'Invitar Pareja' (si no respondió aún)"),
      createBulletPoint("Página 4: [NUEVO si acoplado + completado] Mapa de Fricción Conyugal"),
      createBulletPoint("Página 5: Recomendaciones contextuales (basadas en fricción detectada)"),

      createHeading("6.2 Cambios en DiagnosticReportGenerator", 2),
      createBodyParagraph("El módulo de generación de PDF necesita lógica condicional:"),
      createCodeBlock(`FUNCTION generate_pdf_with_couple_data(user_id, diagnosis_result):
  // Generate standard pages
  pdf_content = generate_standard_pages(diagnosis_result)

  // Check if user has coupling
  coupling = get_coupling_for_user(user_id)

  if coupling:
    if coupling.status == 'pending':
      // Página: Invitar pareja
      pdf_content += generate_invite_section(coupling)

    if coupling.status == 'active' AND coupling.completed_at:
      // Página: Mapa de Fricción
      analysis = get_analysis(coupling.coupling_id)
      pdf_content += generate_friction_map_page(analysis, user_id)

      // Página: Recomendaciones contextuales
      pdf_content += generate_couple_recommendations(analysis)

  // Save to /reports/
  pdf_filename = generate_pdf(pdf_content)
  return pdf_filename
END FUNCTION`),

      createHeading("6.3 Mapa Visual (Gráfica Interactiva)", 2),
      createBodyParagraph("El Mapa se visualiza como:"),
      createBulletPoint("Gráfica de 3 cuadrantes (Alineados | Divergencia Suave | Agujeros Negros) con % de preguntas en cada zona"),
      createBulletPoint("Heatmap por tema: Barra horizontal para cada tema (Ahorro, Deuda, Riesgo, Inversión, Consumo) con código de colores"),
      createBulletPoint("Tabla: Comparativa lado-a-lado de respuestas para temas en rojo"),
      createBulletPoint("Insights en lenguaje natural en español"),

      new Paragraph({ children: [new PageBreak()] }),

      // SECTION 7: TECHNICAL IMPLEMENTATION
      createHeading("7. Detalles Técnicos de Implementación"),

      createHeading("7.1 Blind Mode: Protección de Privacidad", 2),
      createBodyParagraph("Durante el test de Usuario 2, las respuestas se guardan con anonimato temporal:"),
      createCodeBlock(`Flujo Blind:
1. Usuario 2 abre test → Sistema genera BLIND_TEST_ID aleatorio
2. Respuestas se guardan como:
   {
     coupling_id: 'xxx',
     user_id: 'uuid-user2',
     blind_test_id: 'blind-xxx',  // Temporal
     response: 75
   }
3. Usuario 1 NO puede acceder a respuestas de Usuario 2 hasta completar
4. Cuando Usuario 2 termina → Sistema desbloquea visualización Mapa
5. Análisis IA: Cruza ambas respuestas (ya no anónimas, comparación directa)`),

      createHeading("7.2 Encriptación de Magic Link", 2),
      createBodyParagraph("Los tokens de invitación deben ser únicos, no-adivinables y expirables:"),
      createCodeBlock(`TOKEN GENERATION:
  token = generate_secure_random(32 bytes)
  token_hash = hash_with_salt(token, couple_salt)

  // Stored in DB:
  couple_links.link_token = token_hash
  couple_links.link_expires_at = now() + 7 days

  // Returned to user:
  invitation_url = f"https://diagnostico.adapta.com/couple/{token}"

VALIDATION:
  token_hash_input = hash_with_salt(token_from_url, couple_salt)
  if hash matches DB AND expires_at > now():
    allow access
  else:
    error 410 Gone (link expired)`),

      createHeading("7.3 Email Triggers Automáticos", 2),
      createBodyParagraph("Dos eventos de email enviados automáticamente:"),
      createBulletPoint("Evento 1 (Usuario 1 invita): Email a Usuario 2 con link + instrucciones"),
      createBulletPoint("Evento 2 (Usuario 2 completa): Email a ambos con link al Mapa (dentro de 24h)"),
      createBodyParagraph("Configurar en email_triggers.py:"),
      createCodeBlock(`EMAIL_TRIGGER_COUPLE_INVITE = {
  'event': 'couple.invitation.sent',
  'template': 'couple_invite_email.html',
  'delay_seconds': 0
}

EMAIL_TRIGGER_COUPLE_COMPLETE = {
  'event': 'couple.analysis.complete',
  'template': 'couple_map_ready.html',
  'delay_seconds': 3600  # 1 hour after completion
}`),

      createHeading("7.4 Rate Limiting y Validaciones", 2),
      createBulletPoint("Máximo 1 invitación por usuario por 24 horas (evitar spam)"),
      createBulletPoint("Validar que invitado != invitador (mismo email)"),
      createBulletPoint("Validar que invitado no esté ya en coupling activo"),
      createBulletPoint("Bloquear re-invitación a mismo email en 30 días"),

      new Paragraph({ children: [new PageBreak()] }),

      // SECTION 8: EFFORT ESTIMATION
      createHeading("8. Estimación de Esfuerzo (MVP)"),

      createHeading("8.1 Breakdown por Componente", 2),

      createTable([4000, 2000, 3360], [
        ["Componente", "Horas", "Notas"],
        ["Backend: Schema BD", "8h", "Crear 3 tablas + índices + migrations"],
        ["Backend: Endpoints API", "20h", "6 endpoints (invite, signup, answers, analyze, results, decouple)"],
        ["Backend: Algoritmo de Fricción", "16h", "Similitud coseno, divergencia, generación de insights con IA"],
        ["Backend: Email Triggers", "8h", "2 eventos automáticos + templates"],
        ["Frontend: Landing Invitación", "6h", "Minimalista: email+nombre+botón, validaciones"],
        ["Frontend: Test Blind (UI)", "8h", "Adaptación de cuestionario existente, blind mode"],
        ["Frontend: Visualización Mapa", "10h", "Gráficas (Chart.js), heatmap, tabla comparativa"],
        ["PDF: Integración Mapa", "12h", "Generar página PDF + lógica condicional en DiagnosticReportGenerator"],
        ["Testing E2E (Happy Path + Edge Cases)", "8h", "Flujo completo usuario + test de expiración, desacoplamiento"],
        ["Deploy + DevOps", "4h", "DB migrations en Render, env vars, monitoring"],
        ["TOTAL MVP", "100h", "~2.5 semanas (1 dev, 8h/día)"]
      ]),

      createHeading("8.2 Fases de Implementación", 2),
      createHeading("Fase 1: Backend Fundamentals (20h)", 3),
      createBulletPoint("Crear schema BD (8h)"),
      createBulletPoint("Implementar endpoints básicos (12h): invite, signup, answers"),

      createHeading("Fase 2: Algoritmo de Fricción (16h)", 3),
      createBulletPoint("Algoritmo cosine similarity + divergencia (10h)"),
      createBulletPoint("Generación de insights IA (6h)"),

      createHeading("Fase 3: Frontend + PDF (26h)", 3),
      createBulletPoint("Landing + test blind (14h)"),
      createBulletPoint("PDF integration + visualización (12h)"),

      createHeading("Fase 4: Testing + Deploy (8h)", 3),
      createBulletPoint("E2E tests (6h)"),
      createBulletPoint("Deploy a Render (2h)"),

      new Paragraph({ children: [new PageBreak()] }),

      // SECTION 9: RECOMMENDATIONS
      createHeading("9. Recomendaciones Estratégicas"),

      createHeading("9.1 Próximas Iteraciones Post-MVP", 2),
      createBulletPoint("Histórico de Mapas: Permitir a parejas ver evolución en el tiempo (año 1, 2, 3...)"),
      createBulletPoint("Comparativa con Benchmark: '¿Cómo se comparan con parejas similares?'"),
      createBulletPoint("Modo 'Facilitador': Psicólogo/coach puede ver pareja + Mapa + generar plan de acción"),
      createBulletPoint("Integración Stripe: Upsell 'Sesión de parejas' ($250) después del Mapa"),
      createBulletPoint("API Abierta: Que otros asesores integren el Mapa en sus workflows"),

      createHeading("9.2 RGPD & Privacy by Design", 2),
      createBulletPoint("Encriptar responses en BD (per-user keys, como en RGPD v1)"),
      createBulletPoint("Derecho al olvido: Si uno desacopla, sus respuestas se anonimitzan automáticamente"),
      createBulletPoint("Consentimiento: Agregar checkbox 'Compartir análisis anónimo con Adapta para mejora del producto'"),
      createBulletPoint("Audit trail: Registrar cada invitación, lectura de Mapa, desacoplamiento"),

      createHeading("9.3 Viralidad & Marketing", 2),
      createBulletPoint("Open Graph: Meta tags dinámicas para compartir en WhatsApp ('Juan te invitó al Diagnóstico Financiero de parejas')"),
      createBulletPoint("Incentivo de referral: Si pareja completa, ambos reciben 20% dto en 'Taller de Parejas'"),
      createBulletPoint("Share friction map: Botón 'Comparte tu Mapa en Instagram' (imagen + stat: '60% alineados en ahorros')"),

      new Paragraph({ children: [new PageBreak()] }),

      // SECTION 10: TECH STACK
      createHeading("10. Tech Stack Recomendado"),

      createTable([2000, 3000, 4360], [
        ["Capa", "Tecnología", "Por qué"],
        ["Backend", "FastAPI + SQLAlchemy", "Ya en uso; ORM robusto"],
        ["BD", "PostgreSQL", "Soporta JSONB (heatmap), full-text search, ENUM types"],
        ["IA/ML", "OpenAI GPT-4 API", "Generar insights en español natural"],
        ["Frontend", "React + Chart.js", "Gráficas interactivas, responsive"],
        ["PDF Gen", "ReportLab (Python)", "Ya usado en DiagnosticReportGenerator"],
        ["Email", "SendGrid o AWS SES", "Escalable, templates profesionales"],
        ["Auth", "OAuth2 (existing)", "Reutilizar from app_standalone"],
        ["Deploy", "Render", "Ya configurado, environment parity"]
      ]),

      new Paragraph({ children: [new PageBreak()] }),

      // CONCLUSION
      createHeading("Conclusión"),
      createBodyParagraph("El Espejo Fantasma (Couple Mirror) es una característica diferenciadora que convierte el Diagnóstico Financiero en una herramienta de comunicación conyugal. Su implementación requiere ~100 horas e involucra:"),
      createBulletPoint("3 tablas BD nuevas + 6 endpoints API"),
      createBulletPoint("Algoritmo de fricción basado en similitud coseno + insights IA"),
      createBulletPoint("Blind mode para garantizar respuestas honestas"),
      createBulletPoint("PDF integrado con gráficas + CTAs contextuales"),
      createBodyParagraph("El MVP es viable en 2.5-3 semanas con 1 dev. Las fases posteriores abren oportunidades de upsell (sesiones de pareja, talleres, mediación financiera)."),
      createBodyParagraph("La 'viralidad' del Mapa (momento 'aha' de ver juntos) es el motor de crecimiento: parejas querrán compartir resultados, invitar a amigos."),

      new Paragraph({
        children: [new TextRun({
          text: "— Documento generado: Junio 2026 | Versión 1.0 | Ready for Implementation",
          size: 20,
          color: COLORS.accent,
          italics: true
        })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 600 }
      })
    ]
  }
});

// Generate the file
Packer.toBuffer(doc).then(buffer => {
  const outputPath = path.join(
    path.dirname(__filename),
    'ESPEJO_FANTASMA_ARQUITECTURA_TECNICA.docx'
  );
  fs.writeFileSync(outputPath, buffer);
  console.log(`✓ Document generated: ${outputPath}`);
});
