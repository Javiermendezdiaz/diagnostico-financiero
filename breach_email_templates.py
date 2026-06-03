"""
Breach Notification Email Templates
GDPR Art. 33 (Authority notification) & Art. 34 (Individual notification)
Spanish & English versions
"""

from enum import Enum
from datetime import datetime
from typing import Dict, Optional


class BreachEmailTemplates:
    """
    Email templates for GDPR breach notifications.
    Both Art. 33 (authority) and Art. 34 (individual) emails.
    """

    # ========================================================================
    # ART. 33 — AUTHORITY NOTIFICATION (Data Protection Authority)
    # ========================================================================

    @staticmethod
    def art_33_authority_template_es(
        incident_id: str,
        incident_date: datetime,
        affected_count: int,
        severity: str,
        description: str,
        mitigation_steps: Optional[list] = None
    ) -> str:
        """
        Spanish email to Spanish DPA (Agenzia Spagnola di Protezione dei Dati).
        Art. 33 — Notification to supervisory authority within 72 hours.

        Recipients: lopd@aepd.es (Spanish DPA)
        """
        formatted_date = incident_date.strftime("%d de %b de %Y a las %H:%M UTC")
        mitigation_text = ""
        if mitigation_steps:
            mitigation_text = "\n\nMedidas de mitigación adoptadas:\n"
            for step in mitigation_steps:
                action = step.get("action", "Acción desconocida")
                timestamp = step.get("timestamp", "N/A")
                mitigation_text += f"  • {action} ({timestamp})\n"

        return f"""Asunto: Notificación de Incidente de Protección de Datos - {severity} [{incident_id}]

Estimados,

Por medio de la presente, comunicamos un incidente de protección de datos conforme al artículo 33 del RGPD (Reglamento (UE) 2016/679).

---

DATOS DEL INCIDENTE:
ID de Incidente: {incident_id}
Fecha del Incidente: {formatted_date}
Gravedad: {severity}
Usuarios Afectados: {affected_count}

DESCRIPCIÓN:
{description}

DATOS EXPUESTOS:
Los siguientes tipos de datos personales fueron potencialmente comprometidos:
  • Identificadores de usuario
  • Direcciones de correo electrónico
  • Información de perfil
  • Historial de consentimiento

{mitigation_text}

---

INFORMACIÓN DEL RESPONSABLE:
Nombre: Javier Méndez Díaz
Cargo: Controlador de Datos
Empresa: Adaptá Family Office
Contacto: javier@mendezconsultoria.com
Teléfono: +34 [XXX] [XXX] [XXX]

INFORMACIÓN DE SEGURIDAD:
• El sistema ha sido aislado de la red de producción
• Se ha iniciado investigación forense completa
• Se han revisado los registros de acceso (últimos 30 días)
• Se ha verificado la integridad de datos de otros usuarios
• Se ha contactado con nuestro proveedor de hosting

CUMPLIMIENTO NORMATIVO:
✓ Art. 33 RGPD: Notificación a autoridad de control
✓ Art. 32 RGPD: Medidas de seguridad implementadas
✓ Art. 5.1.e RGPD: Registro de auditoría completo mantenido

Confirmamos nuestra total disponibilidad para proporcionar información adicional
y cooperar completamente con la investigación.

Atentamente,

Javier Méndez Díaz
Responsable de Protección de Datos
Adaptá Family Office
javier@mendezconsultoria.com
"""

    @staticmethod
    def art_33_authority_template_en(
        incident_id: str,
        incident_date: datetime,
        affected_count: int,
        severity: str,
        description: str,
        mitigation_steps: Optional[list] = None
    ) -> str:
        """
        English email to supervisory authority (generic).
        Art. 33 — Notification to supervisory authority within 72 hours.
        """
        formatted_date = incident_date.strftime("%d %b %Y at %H:%M UTC")
        mitigation_text = ""
        if mitigation_steps:
            mitigation_text = "\n\nMitigation measures taken:\n"
            for step in mitigation_steps:
                action = step.get("action", "Unknown action")
                timestamp = step.get("timestamp", "N/A")
                mitigation_text += f"  • {action} ({timestamp})\n"

        return f"""Subject: Data Breach Notification - {severity} [{incident_id}]

Dear Supervisory Authority,

We notify you of a personal data breach pursuant to Article 33 of the GDPR (Regulation (EU) 2016/679).

---

BREACH DETAILS:
Incident ID: {incident_id}
Date of Breach: {formatted_date}
Severity: {severity}
Individuals Affected: {affected_count}

DESCRIPTION:
{description}

DATA CATEGORIES AFFECTED:
The following categories of personal data were potentially compromised:
  • User identifiers
  • Email addresses
  • Profile information
  • Consent history

{mitigation_text}

---

DATA CONTROLLER INFORMATION:
Name: Javier Méndez Díaz
Position: Data Controller
Organization: Adaptá Family Office
Contact: javier@mendezconsultoria.com
Phone: +34 [XXX] [XXX] [XXX]

SECURITY MEASURES:
• System isolated from production network
• Full forensic investigation initiated
• Access logs reviewed (last 30 days)
• Data integrity verified for other users
• Hosting provider contacted

GDPR COMPLIANCE:
✓ Art. 33 GDPR: Authority notification
✓ Art. 32 GDPR: Security measures implemented
✓ Art. 5.1.e GDPR: Complete audit trail maintained

We confirm our full availability to provide additional information and cooperate
with any investigation.

Yours faithfully,

Javier Méndez Díaz
Data Protection Lead
Adaptá Family Office
javier@mendezconsultoria.com
"""

    # ========================================================================
    # ART. 34 — INDIVIDUAL NOTIFICATION (Affected Users)
    # ========================================================================

    @staticmethod
    def art_34_individual_template_es(
        user_name: str,
        incident_summary: str,
        data_types_affected: list,
        mitigation_summary: str,
        support_email: str,
        support_phone: Optional[str] = None
    ) -> str:
        """
        Spanish email to affected individuals.
        Art. 34 — Notification to data subjects "without undue delay".
        """
        data_types_text = ", ".join(data_types_affected) if data_types_affected else "información personal"

        return f"""Asunto: Notificación Importante - Incidente de Seguridad en tus Datos Personales

Estimado/a {user_name},

Queremos informarte de un incidente de seguridad que ha afectado tu información personal.
Hemos actuado inmediatamente para proteger tu privacidad y damos transparencia total sobre lo ocurrido.

---

¿QUÉ HA OCURRIDO?

{incident_summary}

INFORMACIÓN AFECTADA:
Los siguientes datos personales pueden haber sido expuestos:
  • {data_types_text}

¿QUIÉN ESTÁ DETRÁS?
Somos Adaptá Family Office, tu asesor de confianza en patrimonio familiar.
Nos compromete la protección de tu información desde el primer día.

---

ACCIONES QUE HEMOS TOMADO

{mitigation_summary}

Además:
✓ Se ha aislado el sistema afectado de nuestra red
✓ Se ha iniciado investigación forense completa
✓ Se han revisado todos los registros de acceso
✓ Se ha reforzado la seguridad en todos nuestros sistemas

---

DERECHOS QUE TE CORRESPONDEN (RGPD)

Tienes derecho a:

1. ACCESO (Art. 15): Solicitar qué datos tuyos procesamos
2. RECTIFICACIÓN (Art. 16): Corregir información inexacta
3. SUPRESIÓN (Art. 17): Solicitar borrado de tus datos
4. PORTABILIDAD (Art. 20): Obtener tus datos en formato transferible
5. OPOSICIÓN (Art. 21): Rechazar ciertos usos de tus datos

Contacta con nosotros para ejercer cualquiera de estos derechos.

---

CÓMO PROTEGERTE

Recomendaciones inmediatas:
  • Cambia tu contraseña si la utilizas en otros servicios
  • Monitorea tu actividad de cuenta en los próximos meses
  • Sospecha de emails de phishing que simulen ser nuestros
  • Activa autenticación de dos factores si está disponible

---

CONTACTO Y SOPORTE

Cualquier duda o preocupación, estamos aquí para ti:

📧 Email de Soporte: {support_email}
"""
        if support_phone:
            return support_phone.join([contact_section := f"☎️ Teléfono: {support_phone}\n", ""])

        return f"""
Atentamente,

Javier Méndez Díaz
Responsable de Protección de Datos
Adaptá Family Office
{support_email}

---

Política de Privacidad: https://www.adaptafamilyoffice.com/privacy
Puedes revisar nuestras prácticas completas de protección de datos aquí.

Esta comunicación cumple con el Artículo 34 del RGPD.
Hemos notificado este incidente a la autoridad de protección de datos competente.
"""

    @staticmethod
    def art_34_individual_template_en(
        user_name: str,
        incident_summary: str,
        data_types_affected: list,
        mitigation_summary: str,
        support_email: str,
        support_phone: Optional[str] = None
    ) -> str:
        """
        English email to affected individuals.
        Art. 34 — Notification to data subjects "without undue delay".
        """
        data_types_text = ", ".join(data_types_affected) if data_types_affected else "personal information"

        contact_info = f"📧 Support Email: {support_email}\n"
        if support_phone:
            contact_info += f"☎️ Phone: {support_phone}\n"

        return f"""Subject: Important Notice - Security Incident Affecting Your Personal Data

Dear {user_name},

We are writing to inform you of a security incident that has affected your personal information.
We have acted immediately to protect your privacy and provide full transparency about what happened.

---

WHAT HAPPENED?

{incident_summary}

INFORMATION AFFECTED:
The following personal data may have been exposed:
  • {data_types_text}

WHO WE ARE:
We are Adaptá Family Office, your trusted family wealth advisor.
We are committed to protecting your information from day one.

---

ACTIONS WE HAVE TAKEN

{mitigation_summary}

Additionally:
✓ The affected system has been isolated from our network
✓ Full forensic investigation has been initiated
✓ All access logs have been reviewed
✓ Security has been enhanced across all systems

---

YOUR RIGHTS UNDER GDPR

You have the right to:

1. ACCESS (Art. 15): Request what data we process about you
2. RECTIFICATION (Art. 16): Correct inaccurate information
3. ERASURE (Art. 17): Request deletion of your data
4. PORTABILITY (Art. 20): Obtain your data in transferable format
5. OBJECTION (Art. 21): Oppose certain uses of your data

Contact us to exercise any of these rights.

---

HOW TO PROTECT YOURSELF

Immediate recommendations:
  • Change your password if you use it on other services
  • Monitor your account activity over the coming months
  • Be suspicious of phishing emails impersonating us
  • Enable two-factor authentication if available

---

SUPPORT & CONTACT

We're here for any questions or concerns:

{contact_info}

Sincerely,

Javier Méndez Díaz
Data Protection Lead
Adaptá Family Office
{support_email}

---

Privacy Policy: https://www.adaptafamilyoffice.com/privacy
Review our complete data protection practices here.

This communication complies with Article 34 of the GDPR.
We have notified this incident to the relevant supervisory authority.
"""

    @staticmethod
    def get_template(
        template_type: str,
        language: str = "es",
        **kwargs
    ) -> str:
        """
        Get email template by type and language.

        Args:
            template_type: "art_33_authority" or "art_34_individual"
            language: "es" (Spanish) or "en" (English)
            **kwargs: Template-specific parameters

        Returns:
            Formatted email body
        """
        if template_type == "art_33_authority":
            if language == "es":
                return BreachEmailTemplates.art_33_authority_template_es(**kwargs)
            else:
                return BreachEmailTemplates.art_33_authority_template_en(**kwargs)

        elif template_type == "art_34_individual":
            if language == "es":
                return BreachEmailTemplates.art_34_individual_template_es(**kwargs)
            else:
                return BreachEmailTemplates.art_34_individual_template_en(**kwargs)

        else:
            raise ValueError(f"Unknown template type: {template_type}")


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    from datetime import datetime

    # Example Art. 33 (Authority) notification
    print("=" * 70)
    print("ART. 33 AUTHORITY NOTIFICATION (SPANISH)")
    print("=" * 70)

    art_33_es = BreachEmailTemplates.get_template(
        template_type="art_33_authority",
        language="es",
        incident_id="BREACH-2026-0530-001",
        incident_date=datetime(2026, 5, 30, 14, 30),
        affected_count=147,
        severity="HIGH",
        description="Acceso no autorizado a la base de datos de clientes mediante inyección SQL no parcheada.",
        mitigation_steps=[
            {"action": "Sistema aislado de red de producción", "timestamp": "2026-05-30T14:35Z"},
            {"action": "Credenciales comprometidas rotadas", "timestamp": "2026-05-30T15:00Z"},
            {"action": "Parches de seguridad aplicados", "timestamp": "2026-05-30T16:45Z"},
        ]
    )
    print(art_33_es)

    print("\n" + "=" * 70)
    print("ART. 34 INDIVIDUAL NOTIFICATION (SPANISH)")
    print("=" * 70)

    art_34_es = BreachEmailTemplates.get_template(
        template_type="art_34_individual",
        language="es",
        user_name="María García López",
        incident_summary="Nuestro sistema fue afectado por un intento de acceso no autorizado. Aunque la mayoría de usuarios no fueron impactados, tu correo y algunos datos de perfil pueden haber sido expuestos.",
        data_types_affected=["correo electrónico", "nombre completo", "teléfono"],
        mitigation_summary="Hemos aislado inmediatamente el sistema, revisado todos los registros y reforzado nuestras defensas. Tu información ha sido protegida con encriptación de extremo a extremo desde ese momento.",
        support_email="soporte@adaptafamilyoffice.com",
        support_phone="+34 912 345 678"
    )
    print(art_34_es)

    print("\n" + "=" * 70)
    print("ART. 34 INDIVIDUAL NOTIFICATION (ENGLISH)")
    print("=" * 70)

    art_34_en = BreachEmailTemplates.get_template(
        template_type="art_34_individual",
        language="en",
        user_name="John Smith",
        incident_summary="Our system was affected by an unauthorized access attempt. While most users were not impacted, your email and some profile data may have been exposed.",
        data_types_affected=["email address", "full name", "phone number"],
        mitigation_summary="We immediately isolated the system, reviewed all logs, and reinforced our defenses. Your information has been protected with end-to-end encryption since that time.",
        support_email="support@adaptafamilyoffice.com",
        support_phone="+34 912 345 678"
    )
    print(art_34_en)

    print("\n✓ Email templates loaded successfully")
