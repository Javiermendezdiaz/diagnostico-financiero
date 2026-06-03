#!/usr/bin/env node
/**
 * ESPEJO FANTASMA - Complete Technical Architecture Document
 * Generates comprehensive technical design in Word format
 */

const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, PageBreak,
        AlignmentType, WidthType, BorderStyle, ShadingType, HeadingLevel, VerticalAlign,
        LevelFormat } = require('docx');
const fs = require('fs');
const path = require('path');

// Color scheme
const COLORS = {
  primary: "1a1a1a",
  accent: "FFB81C",
  green: "388E3C",
  yellow: "FBC02D",
  red: "D32F2F",
  lightBg: "F5F5F5",
  border: "CCCCCC",
  text: "333333"
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
        children: [
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

function createBodyParagraph(text) {
  return new Paragraph({
    children: [new TextRun({ text, size: 22, color: COLORS.text })],
    spacing: { line: 360, after: 120 }
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

// Build document children array
const children = [
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
      text: "Mapa de Friccion Conyugal",
      size: 32,
      color: COLORS.accent,
      bold: true
    })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 600 }
  }),
  new Paragraph({
    children: [new TextRun({
      text: "Arquitectura Tecnica Completa para Diagnostico Financiero",
      size: 24,
      color: COLORS.text,
      italics: true
    })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 1200 }
  }),
  new Paragraph({
    children: [new TextRun({
      text: "Version: 1.0 | Fecha: Junio 2026 | Estate: DISENO ARQUITECTONICO",
      size: 22,
      color: COLORS.text
    })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 1800 }
  }),
  new Paragraph({ children: [new PageBreak()] }),

  // SECTION 1
  createHeading("1. Resolucion de Preguntas Criticas"),
  createBodyParagraph("Antes de proceder con la arquitectura, se responden las 5 preguntas estrategicas que definen el alcance:"),

  createHeading("1.1 Cuantas preguntas de Familia y Dinero son?", 2),
  createBodyParagraph("El schema actual de 500 preguntas organizados en 10 capas no tiene una seccion explicita 'Familia y Dinero'. Existen ~35-40 preguntas en varias capas sobre dinamicas conyugales."),
  createBodyParagraph("DECISION ARQUITECTONICA: Crear una NUEVA capa 'Familia y Dinero' con 50 preguntas enfocadas 100% en dinamicas conyugales. Mas limpio que fragmentar en multiples capas."),

  createHeading("1.2 Email para invitar pareja o solo link+WhatsApp?", 2),
  createBodyParagraph("RECOMENDACION: Ambos. El sistema genera un magic link unico que se puede copiar y compartir vía WhatsApp (mas rapido) o enviar vía email (mas profesional)."),

  createHeading("1.3 Cuando se muestra el Mapa?", 2),
  createBodyParagraph("DECISION: Solo DESPUES. Usuario 1 completa test completo → PDF individual. Usuario 1 invita pareja → Pareja completa solo 'Familia y Dinero' (blind mode). Pareja completa → Se desbloquea Mapa en ambos PDFs."),

  createHeading("1.4 Puede una pareja desacoplarse?", 2),
  createBodyParagraph("DECISION: SI, pero con restricciones. La tabla couple_links permite estado 'decoupled_at'. Mantiene auditoría, permite nueva pareja, bloquea re-invitaciones al mismo email, no borra datos historicos."),

  createHeading("1.5 CTA especifico despues del Mapa?", 2),
  createBodyParagraph("RECOMENDACION: CTAs contextuales según friccion detectada:"),
  createBulletPoint("ALINEADOS (Verde): 'Excelente. Reserva sesion de pareja'"),
  createBulletPoint("DIVERGENCIA SUAVE (Amarillo): 'Taller Dinero sin Conflicto'"),
  createBulletPoint("AGUJEROS NEGROS (Rojo): 'Sesion de mediacion financiera'"),

  new Paragraph({ children: [new PageBreak()] }),

  // SECTION 2
  createHeading("2. Flujo UX: Paso a Paso"),
  createHeading("2.1 Usuario 1 (Invitador)", 2),
  createBulletPoint("Completa cuestionario de 500 preguntas"),
  createBulletPoint("Llega a pantalla Resultados con PDF generado"),
  createBulletPoint("Ve seccion: Tienes pareja?"),
  createBulletPoint("Si elige SI: Boton Invitar Pareja (color accent)"),
  createBulletPoint("Sistema genera magic link → copia a portapapeles"),
  createBulletPoint("Instrucciones: Envia este link a tu pareja por WhatsApp o email"),

  createHeading("2.2 Usuario 2 (Invitado)", 2),
  createBulletPoint("Recibe link: https://diagnostico.adapta.com/couple/abc123xyz"),
  createBulletPoint("Landing minimalista: Tu pareja te invito a responder 50 preguntas"),
  createBulletPoint("Signup ultra-rapido: Email + Nombre (validar != Usuario 1)"),
  createBulletPoint("Boton: Responder preguntas → Entra a modo Blind"),
  createBulletPoint("Responde SOLO 50 preguntas de Familia y Dinero"),
  createBulletPoint("Sin acceso a respuestas de Usuario 1"),
  createBulletPoint("Al terminar: Listo! Tu pareja vera el Mapa en 24 horas"),

  createHeading("2.3 Generacion del Mapa (Backend)", 2),
  createBulletPoint("Trigger: POST /api/couple/analyze after Usuario 2 completes"),
  createBulletPoint("IA compara puntajes tema-por-tema"),
  createBulletPoint("Calcula divergencia: cosine similarity entre vectores"),
  createBulletPoint("Clasifica 3 zonas: ALINEADOS (diff<15%), DIVERGENCIA SUAVE (15-40%), AGUJEROS NEGROS (>40%)"),
  createBulletPoint("Genera JSON + PDF con grafica interactiva"),
  createBulletPoint("Envia email a ambos: Tu Mapa esta listo"),

  new Paragraph({ children: [new PageBreak()] }),

  // SECTION 3
  createHeading("3. Schema de Base de Datos (SQL)"),
  createHeading("3.1 Tablas Nuevas", 2),

  createHeading("Tabla: couple_links", 3),
  createCodeBlock(`CREATE TABLE couple_links (
  coupling_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user1_id UUID NOT NULL REFERENCES users(id),
  user2_id UUID NULLABLE REFERENCES users(id),
  link_token VARCHAR(256) UNIQUE NOT NULL,
  link_expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '7 days',
  completed_at TIMESTAMP NULLABLE,
  decoupled_at TIMESTAMP NULLABLE,
  status ENUM('pending','active','decoupled','expired') DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`),

  createHeading("Tabla: couple_responses", 3),
  createCodeBlock(`CREATE TABLE couple_responses (
  response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coupling_id UUID NOT NULL REFERENCES couple_links(coupling_id),
  user_id UUID NOT NULL REFERENCES users(id),
  question_id VARCHAR(50) NOT NULL,
  question_topic VARCHAR(50),
  score_numeric INT CHECK (score_numeric BETWEEN 0 AND 100),
  is_blind BOOLEAN DEFAULT TRUE,
  answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`),

  createHeading("Tabla: couple_analysis_results", 3),
  createCodeBlock(`CREATE TABLE couple_analysis_results (
  analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coupling_id UUID NOT NULL REFERENCES couple_links(coupling_id),
  overall_similarity NUMERIC(5,2),
  topic_similarities JSONB,
  friction_zones JSONB,
  ai_insights_es TEXT,
  pdf_path VARCHAR(500) NULLABLE,
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`),

  createHeading("3.2 Modificacion a users", 3),
  createCodeBlock(`ALTER TABLE users ADD COLUMN (
  partner_id UUID NULLABLE REFERENCES users(id),
  couple_relationship_status ENUM('single','coupled','decoupled') DEFAULT 'single'
);`),

  new Paragraph({ children: [new PageBreak()] }),

  // SECTION 4
  createHeading("4. Endpoints API"),

  createHeading("4.1 POST /api/couple/invite-partner", 2),
  createCodeBlock(`REQUEST: {
  "user_id": "uuid-user1",
  "partner_email": "partner@example.com",
  "send_email": true
}

RESPONSE (201): {
  "coupling_id": "uuid-coupling",
  "link_token": "abc123xyz",
  "invitation_url": "https://diagnostico.adapta.com/couple/abc123xyz"
}`),

  createHeading("4.2 GET /api/couple/{link_token}", 2),
  createBodyParagraph("Landing minimalista. Retorna info basica de invitacion."),

  createHeading("4.3 POST /api/couple/signup-and-start-test", 2),
  createBodyParagraph("Usuario 2 se registra (ultra-rapido) y comienza test blind."),

  createHeading("4.4 POST /api/couple/answers", 2),
  createBodyParagraph("Pareja envia respuestas individuales (blind mode)."),

  createHeading("4.5 POST /api/couple/analyze", 2),
  createBodyParagraph("Backend: Analisis IA + generacion de Mapa. Trigger automatico."),

  createHeading("4.6 GET /api/couple/results/{coupling_id}", 2),
  createBodyParagraph("Retorna Mapa completo (JSON + PDF path)."),

  createHeading("4.7 POST /api/couple/decouple", 2),
  createBodyParagraph("Usuario desvincula pareja (soft delete, no borra datos)."),

  new Paragraph({ children: [new PageBreak()] }),

  // SECTION 5
  createHeading("5. Algoritmo de Friccion Conyugal"),

  createHeading("5.1 Metodos", 2),
  createBulletPoint("Cosine Similarity: Calcula similitud entre vectores de respuestas"),
  createBulletPoint("Divergencia por Tema: Calcula euclidiana en cada tema (ahorro, deuda, etc)"),
  createBulletPoint("Deteccion de Contradicciones: Preguntas pareadas con desacuerdo directo"),

  createHeading("5.2 Pseudocodigo", 2),
  createCodeBlock(`FUNCTION analyze_couple_friction(coupling_id):
  u1_responses = get_responses(coupling_id, user1_id)
  u2_responses = get_responses(coupling_id, user2_id)

  overall_similarity = cosine_similarity(u1, u2) * 100

  topic_similarities = {}
  for topic in [ahorro, deuda, riesgo, inversion, consumo]:
    topic_similarities[topic] = cosine_similarity(
      topic_responses_u1, topic_responses_u2
    ) * 100

  friction_zones = classify_zones(topic_similarities)
  insights = generate_insights(overall_similarity, topic_similarities)

  save_analysis(coupling_id, {overall_similarity, topic_similarities, insights})
  generate_pdf(coupling_id)
  send_emails(coupling_id)
END`),

  createHeading("5.3 Umbrales de Clasificacion", 2),
  createBulletPoint("ALINEADOS (Verde): > 85% similitud"),
  createBulletPoint("DIVERGENCIA SUAVE (Amarillo): 60-85% similitud"),
  createBulletPoint("AGUJEROS NEGROS (Rojo): < 60% similitud"),

  new Paragraph({ children: [new PageBreak()] }),

  // SECTION 6
  createHeading("6. Integracion PDF"),

  createHeading("6.1 Estructura del PDF Actualizado", 2),
  createBulletPoint("Pagina 1-2: Resultados diagnostico individual (existente)"),
  createBulletPoint("Pagina 3: [NUEVO si acoplado] Seccion Invitar Pareja"),
  createBulletPoint("Pagina 4: [NUEVO si acoplado+completado] Mapa de Friccion Conyugal"),
  createBulletPoint("Pagina 5: Recomendaciones contextuales"),

  createHeading("6.2 Cambios en DiagnosticReportGenerator", 2),
  createCodeBlock(`FUNCTION generate_pdf_with_couple_data(user_id, diagnosis):
  pdf = generate_standard_pages(diagnosis)

  coupling = get_coupling_for_user(user_id)
  if coupling:
    if coupling.status == 'pending':
      pdf += generate_invite_section(coupling)
    if coupling.status == 'active' AND coupling.completed_at:
      analysis = get_analysis(coupling.coupling_id)
      pdf += generate_friction_map_page(analysis)
      pdf += generate_couple_recommendations(analysis)

  save_pdf(pdf)
  return pdf_filename
END`),

  new Paragraph({ children: [new PageBreak()] }),

  // SECTION 7
  createHeading("7. Estimacion de Esfuerzo (MVP)"),

  createTable([4000, 2000, 3360], [
    ["Componente", "Horas", "Notas"],
    ["Backend: Schema BD", "8h", "Crear 3 tablas + indices"],
    ["Backend: Endpoints API", "20h", "6 endpoints"],
    ["Backend: Algoritmo", "16h", "Similitud coseno + divergencia + IA"],
    ["Backend: Email Triggers", "8h", "2 eventos automaticos"],
    ["Frontend: Landing", "6h", "Minimalista: email+nombre+boton"],
    ["Frontend: Test Blind", "8h", "Adaptacion cuestionario"],
    ["Frontend: Visualizacion", "10h", "Graficas + heatmap"],
    ["PDF: Integracion", "12h", "Generacion pagina + logica condicional"],
    ["Testing E2E", "8h", "Flujo completo + edge cases"],
    ["Deploy", "4h", "DB migrations + env vars"],
    ["TOTAL MVP", "100h", "~2.5 semanas (1 dev, 8h/dia)"]
  ]),

  createHeading("7.1 Fases de Implementacion", 2),
  createHeading("Fase 1: Backend Fundamentals (20h)", 3),
  createBulletPoint("Crear schema BD (8h)"),
  createBulletPoint("Endpoints basicos (12h): invite, signup, answers"),

  createHeading("Fase 2: Algoritmo (16h)", 3),
  createBulletPoint("Similitud coseno + divergencia (10h)"),
  createBulletPoint("Generacion de insights IA (6h)"),

  createHeading("Fase 3: Frontend + PDF (26h)", 3),
  createBulletPoint("Landing + test blind (14h)"),
  createBulletPoint("PDF + visualizacion (12h)"),

  createHeading("Fase 4: Testing + Deploy (8h)", 3),
  createBulletPoint("E2E tests (6h)"),
  createBulletPoint("Deploy (2h)"),

  new Paragraph({ children: [new PageBreak()] }),

  // SECTION 8
  createHeading("8. Tech Stack Recomendado"),

  createTable([2000, 3000, 4360], [
    ["Capa", "Tecnologia", "Por que"],
    ["Backend", "FastAPI + SQLAlchemy", "Ya en uso; ORM robusto"],
    ["BD", "PostgreSQL", "JSONB, full-text, ENUM"],
    ["IA/ML", "OpenAI GPT-4", "Insights en espanol natural"],
    ["Frontend", "React + Chart.js", "Graficas interactivas"],
    ["PDF Gen", "ReportLab", "Ya usado"],
    ["Email", "SendGrid o AWS SES", "Escalable"],
    ["Auth", "OAuth2", "Reutilizar"],
    ["Deploy", "Render", "Ya configurado"]
  ]),

  new Paragraph({ children: [new PageBreak()] }),

  // CONCLUSION
  createHeading("9. Conclusion"),
  createBodyParagraph("El Espejo Fantasma (Couple Mirror) es una caracteristica diferenciadora que convierte el Diagnostico Financiero en una herramienta de comunicacion conyugal."),
  createBodyParagraph("Implementacion: ~100 horas, 3 tablas BD nuevas, 6 endpoints API, algoritmo de friccion con similitud coseno + insights IA, blind mode, PDF integrado con graficas + CTAs contextuales."),
  createBodyParagraph("MVP viable en 2.5-3 semanas con 1 dev. Abre oportunidades de upsell (sesiones de pareja, talleres, mediacion financiera)."),
  createBodyParagraph("Viralidad: El Mapa (momento 'aha' de ver juntos) es el motor de crecimiento. Parejas querran compartir resultados."),

  new Paragraph({
    children: [new TextRun({
      text: "Documento generado: Junio 2026 | Version 1.0 | Ready for Implementation",
      size: 20,
      color: COLORS.accent,
      italics: true
    })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 600 }
  })
];

// Create document
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
      }
    ]
  },
  styles: {
    default: {
      document: { run: { font: "Arial", size: 22 }, paragraph: { spacing: { line: 360 } } }
    }
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children
  }]
});

// Generate file
Packer.toBuffer(doc).then(buffer => {
  const outputPath = path.join(
    path.dirname(__filename),
    'ESPEJO_FANTASMA_ARQUITECTURA_TECNICA.docx'
  );
  fs.writeFileSync(outputPath, buffer);
  console.log(`✓ Document generated: ${outputPath}`);
  console.log(`✓ File size: ${(buffer.length / 1024).toFixed(2)} KB`);
}).catch(err => {
  console.error("Error generating document:", err);
  process.exit(1);
});
