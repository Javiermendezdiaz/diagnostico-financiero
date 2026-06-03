#!/usr/bin/env python3
"""
Couple Mirror Fantasma - Models & Matching Engine
Sincronización ciega semántica para parejas.
"""

import json
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib

# ============ MODELS ============

@dataclass
class CoupleSession:
    """Sesión de pareja ciega"""
    id: str
    user_id: str
    user_email: str
    partner_email: Optional[str] = None
    partner_id: Optional[str] = None
    status: str = "pending"  # pending|invited|accepted|in_progress|completed
    invite_token: str = ""
    invite_expires_at: Optional[str] = None
    user_section_8_responses: Optional[Dict] = None
    partner_section_8_responses: Optional[Dict] = None
    alignment_score: Optional[float] = None
    friction_zones: Optional[List[Dict]] = None
    general_narrative: Optional[str] = None
    created_at: str = ""
    completed_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)


class CoupleSessionStore:
    """In-memory storage + JSON backup para sesiones de pareja"""

    def __init__(self, backup_path: str = "couple_sessions.json"):
        self.sessions: Dict[str, CoupleSession] = {}
        self.backup_path = backup_path
        self.token_index: Dict[str, str] = {}  # token -> session_id
        self._load_backup()

    def _load_backup(self):
        """Cargar sesiones de respaldo JSON"""
        try:
            with open(self.backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for sid, session_dict in data.items():
                    session = CoupleSession(**session_dict)
                    self.sessions[sid] = session
                    if session.invite_token:
                        self.token_index[session.invite_token] = sid
        except FileNotFoundError:
            pass

    def _save_backup(self):
        """Guardar sesiones a JSON"""
        data = {sid: s.to_dict() for sid, s in self.sessions.items()}
        with open(self.backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    def create_session(self, user_id: str, user_email: str) -> CoupleSession:
        """Crear nueva sesión de pareja"""
        session = CoupleSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_email=user_email,
            status="pending",
            created_at=datetime.utcnow().isoformat()
        )
        self.sessions[session.id] = session
        self._save_backup()
        return session

    def send_invite(self, session_id: str, partner_email: str) -> str:
        """Enviar invitación a pareja, retorna token"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Session not found")

        token = secrets.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(hours=48)).isoformat()

        session.partner_email = partner_email
        session.status = "invited"
        session.invite_token = token
        session.invite_expires_at = expires_at

        self.token_index[token] = session_id
        self._save_backup()

        return token

    def accept_invite(self, token: str, partner_id: str) -> Optional[CoupleSession]:
        """Pareja acepta invitación"""
        session_id = self.token_index.get(token)
        if not session_id:
            return None

        session = self.sessions.get(session_id)
        if not session:
            return None

        # Validar que token no ha expirado
        if session.invite_expires_at:
            expires = datetime.fromisoformat(session.invite_expires_at)
            if datetime.utcnow() > expires:
                return None

        session.partner_id = partner_id
        session.status = "accepted"
        session.invite_token = ""  # Invalidar token

        self._save_backup()
        return session

    def submit_user_responses(self, session_id: str, responses: Dict) -> bool:
        """Usuario envía respuestas Sección 8"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.user_section_8_responses = responses
        session.status = "in_progress"
        self._save_backup()
        return True

    def submit_partner_responses(self, session_id: str, responses: Dict) -> bool:
        """Pareja envía respuestas Sección 8"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.partner_section_8_responses = responses
        session.status = "in_progress"
        self._save_backup()
        return True

    def complete_session(self, session_id: str, friction_data: Dict) -> bool:
        """Completar sesión con resultados matcher"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.alignment_score = friction_data.get('alignment_score')
        session.friction_zones = friction_data.get('friction_zones')
        session.general_narrative = friction_data.get('general_narrative')
        session.status = "completed"
        session.completed_at = datetime.utcnow().isoformat()

        self._save_backup()
        return True

    def get_session(self, session_id: str) -> Optional[CoupleSession]:
        """Obtener sesión por ID"""
        return self.sessions.get(session_id)

    def get_session_by_token(self, token: str) -> Optional[CoupleSession]:
        """Obtener sesión por invite token"""
        session_id = self.token_index.get(token)
        return self.sessions.get(session_id) if session_id else None


# ============ FRICTION MATCHING ENGINE ============

class CoupleMatchingEngine:
    """Motor de alineación de parejas por 5 dimensiones"""

    FRICTION_DIMENSIONS = {
        'ahorro_anual': {
            'weight': 0.25,
            'max_gap': 100000,
            'narrative_template': 'Capacidad anual de ahorro diferente: esperabais divergencia de {gap:,.0f}€'
        },
        'horizonte_libertad': {
            'weight': 0.20,
            'max_gap': 30,
            'narrative_template': 'Horizonte temporal distinto: {gap} años de diferencia en expectativa'
        },
        'tolerancia_riesgo': {
            'weight': 0.20,
            'max_gap': 100,
            'narrative_template': 'Perfiles de riesgo complementarios: uno conservador, otro dinámico'
        },
        'gasto_presente': {
            'weight': 0.20,
            'max_gap': 50000,
            'narrative_template': 'Visiones del gasto presente desfasadas: {gap:,.0f}€ anuales de diferencia'
        },
        'herencia_planes': {
            'weight': 0.15,
            'max_gap': 100,
            'narrative_template': 'Visiones sobre herencia e intención generacional distintas'
        }
    }

    @classmethod
    def calculate_alignment(cls, user_responses: Dict, partner_responses: Dict) -> Dict:
        """
        Calcular alineación entre pareja.
        Retorna: {
            alignment_score: 0-100,
            friction_zones: [{dimension, gap, severity, narrative}],
            general_narrative: str,
            recommendation: str
        }
        """

        # Extracto valores clave de ambos (ignoramos si falta alguno, asumimos default)
        def safe_get(resp, key, default=0):
            return resp.get(key, default)

        # Dimensión 1: Ahorro anual
        ahorro_user = safe_get(user_responses, 'ahorro_anual', 10000)
        ahorro_partner = safe_get(partner_responses, 'ahorro_anual', 10000)
        gap_ahorro = abs(ahorro_user - ahorro_partner)

        # Dimensión 2: Horizonte libertad (años)
        horizonte_user = safe_get(user_responses, 'horizonte_libertad', 20)
        horizonte_partner = safe_get(partner_responses, 'horizonte_libertad', 20)
        gap_horizonte = abs(horizonte_user - horizonte_partner)

        # Dimensión 3: Tolerancia riesgo (0-100)
        riesgo_user = safe_get(user_responses, 'tolerancia_riesgo', 50)
        riesgo_partner = safe_get(partner_responses, 'tolerancia_riesgo', 50)
        gap_riesgo = abs(riesgo_user - riesgo_partner)

        # Dimensión 4: Gasto presente anual
        gasto_user = safe_get(user_responses, 'gasto_presente', 20000)
        gasto_partner = safe_get(partner_responses, 'gasto_presente', 20000)
        gap_gasto = abs(gasto_user - gasto_partner)

        # Dimensión 5: Herencia planes (0-100 alineación esperada)
        herencia_user = safe_get(user_responses, 'herencia_planes', 50)
        herencia_partner = safe_get(partner_responses, 'herencia_planes', 50)
        gap_herencia = abs(herencia_user - herencia_partner)

        # Calcular severidad (0-1) por dimensión
        gaps = {
            'ahorro_anual': gap_ahorro,
            'horizonte_libertad': gap_horizonte,
            'tolerancia_riesgo': gap_riesgo,
            'gasto_presente': gap_gasto,
            'herencia_planes': gap_herencia
        }

        friction_zones = []
        weighted_severity = 0

        for dim_name, gap_value in gaps.items():
            dim_config = cls.FRICTION_DIMENSIONS[dim_name]
            max_gap = dim_config['max_gap']
            weight = dim_config['weight']

            # Severidad normalizada (0-1): gap / max_gap
            severity_norm = min(1.0, gap_value / max_gap) if max_gap > 0 else 0
            weighted_severity += severity_norm * weight

            # Determinar nivel (low|medium|high)
            if severity_norm < 0.3:
                severity_level = 'low'
                severity_icon = '🟢'
            elif severity_norm < 0.7:
                severity_level = 'medium'
                severity_icon = '🟡'
            else:
                severity_level = 'high'
                severity_icon = '🔴'

            # Generar narrativa constructiva
            narrative = cls._generate_friction_narrative(
                dim_name, gap_value, severity_level, user_responses, partner_responses
            )

            friction_zones.append({
                'dimension': dim_name,
                'gap': gap_value,
                'severity': severity_level,
                'severity_icon': severity_icon,
                'narrative': narrative
            })

        # Alignment score: 100 - (weighted_severity * 100)
        alignment_score = max(0, 100 - (weighted_severity * 100))

        # Narrativa general
        general_narrative = cls._generate_general_narrative(alignment_score, friction_zones)

        # Recomendación
        recommendation = cls._generate_recommendation(alignment_score, friction_zones)

        return {
            'alignment_score': round(alignment_score, 1),
            'friction_zones': friction_zones,
            'general_narrative': general_narrative,
            'recommendation': recommendation
        }

    @staticmethod
    def _generate_friction_narrative(dimension: str, gap: float, severity: str,
                                     user_resp: Dict, partner_resp: Dict) -> str:
        """Narrativa constructiva por dimensión (nunca acusatoria)"""

        if dimension == 'ahorro_anual':
            if severity == 'high':
                return f"Diferencia significativa en capacidad de ahorro (€{gap:,.0f}). Recomendado: pactar presupuesto conjunto con 'colchón' flexible."
            elif severity == 'medium':
                return f"Visiones de ahorro moderadamente distintas (€{gap:,.0f}). Plantear revisión semestral de objetivos."
            else:
                return "Alineación fuerte en capacidad de ahorro. Excelente base para planes comunes."

        elif dimension == 'horizonte_libertad':
            if severity == 'high':
                return f"Expectativas de libertad financiera divergen ~{gap} años. Necesario: conversar sobre timeline vital (retiro, hijos, cambios laborales)."
            elif severity == 'medium':
                return f"Horizonte levemente distinto (~{gap} años). Plantear metas intermedias anuales para sincronizar."
            else:
                return "Comparten visión de futuro temporal. Base sólida para inversiones a largo plazo."

        elif dimension == 'tolerancia_riesgo':
            if severity == 'high':
                return "Perfiles de riesgo muy distintos. Recomendado: portfolio segregado con 'zona neutra' común (bonos, depósitos)."
            elif severity == 'medium':
                return "Uno más conservador, otro más dinámico. Excelente para balance: copiad decisiones inversoras con veto mutuo."
            else:
                return "Ambos comparten propensión al riesgo. Clarificar juntos límites de volatilidad aceptable."

        elif dimension == 'gasto_presente':
            if severity == 'high':
                return f"Diferencia anual notable en gasto (€{gap:,.0f}). Recomendado: presupuesto 'core' común + asignación personal flexible."
            elif severity == 'medium':
                return f"Estilos de gasto moderadamente distintos (€{gap:,.0f}). Plantear: 50% común + 50% autonomía."
            else:
                return "Alineación en gasto diario. Fácil gestión de presupuesto compartido."

        elif dimension == 'herencia_planes':
            if severity == 'high':
                return "Visiones sobre legado generacional muy distintas. Conversación profunda recomendada con asesor patrimonial + mediador."
            elif severity == 'medium':
                return "Intenciones generacionales levemente dispares. Clarificar: ¿hijos? ¿Causas? ¿Cuándo documentar?"
            else:
                return "Comparten visión sobre legado. Proceder a formalizar testamento y poderes."

        return "Dimensión evaluada. Recomendado revisar con asesor."

    @staticmethod
    def _generate_general_narrative(score: float, friction_zones: List[Dict]) -> str:
        """Narrativa constructiva sobre alineación general"""

        if score >= 85:
            return (
                "🟢 **Alineación Excelente.** Vuestros perfiles financieros están coherentes. "
                "El dinero probablemente NO es fuente de fricción en la relación. "
                "Recomendado: mantener diálogos anuales sobre cambios de vida y revisar plan cada 2-3 años."
            )
        elif score >= 70:
            return (
                "🟡 **Alineación Buena.** Hay convergencia en lo fundamental, aunque algunos puntos merecen atención. "
                "Estos gaps son NORMALES en parejas. Recomendado: sesión de planificación trimestral, especialmente en dimensiones marcadas."
            )
        elif score >= 50:
            return (
                "🟡 **Alineación Moderada.** Existen diferencias notables que pueden generar tensión si no se gestionan. "
                "Esto no es 'incompatibilidad', es que esperabais dinero de forma distinta. Recomendado: asesor financiero independiente + diálogo sin juicio."
            )
        else:
            return (
                "🔴 **Alineación Baja.** Vuestras visiones financieras están significativamente desalineadas. "
                "NO es insalvable, pero necesita atención profesional. Recomendado: mediador financiero + plan de reconversión de expectativas."
            )

    @staticmethod
    def _generate_recommendation(score: float, friction_zones: List[Dict]) -> str:
        """Recomendación accionable"""

        # Filtra zonas altas de fricción
        high_friction = [z for z in friction_zones if z['severity'] == 'high']

        if high_friction:
            dims_text = ", ".join([z['dimension'].replace('_', ' ') for z in high_friction])
            return f"Prioridad: taller de alineación en {dims_text}. Buscar asesor financiero familiar especializado en parejas."

        if score < 70:
            return "Programar sesión de planificación conjunta. Recomendamos framework '3+3+3': auditoría (3h) + plan (3h) + follow-up (3h/año)."

        return "Mantener revisión anual. Este tipo de datos mejora cuando se dialoga sin presión."
