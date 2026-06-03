import nodemailer from 'nodemailer';
import { GDPRRequest, User } from '../types';

interface EmailConfig {
  host: string;
  port: number;
  secure: boolean;
  auth: {
    user: string;
    pass: string;
  };
  from: string;
}

class EmailService {
  private transporter: nodemailer.Transporter;
  private config: EmailConfig;
  private enabled: boolean;

  constructor() {
    this.config = {
      host: process.env.SMTP_HOST || 'smtp.gmail.com',
      port: parseInt(process.env.SMTP_PORT || '587'),
      secure: process.env.SMTP_SECURE === 'true',
      auth: {
        user: process.env.SMTP_USER || '',
        pass: process.env.SMTP_PASS || '',
      },
      from: process.env.SMTP_FROM || 'noreply@gdpr-app.com',
    };

    this.enabled = !!(this.config.auth.user && this.config.auth.pass);

    if (this.enabled) {
      this.transporter = nodemailer.createTransport(this.config);
    }
  }

  /**
   * Envía notificación de cambio de estado de solicitud
   */
  async sendStatusChangeNotification(
    user: User,
    request: GDPRRequest,
    previousStatus: string
  ): Promise<boolean> {
    if (!this.enabled) {
      console.warn('Email service disabled: SMTP credentials not configured');
      return false;
    }

    try {
      const subject = this.getSubjectForStatus(request.status);
      const htmlContent = this.getEmailTemplate(user, request, previousStatus);

      await this.transporter.sendMail({
        from: this.config.from,
        to: user.email,
        subject,
        html: htmlContent,
        text: this.stripHtml(htmlContent),
      });

      console.log(`Email sent to ${user.email} for request ${request.id}`);
      return true;
    } catch (error) {
      console.error(`Failed to send email to ${user.email}:`, error);
      return false;
    }
  }

  /**
   * Envía notificación de registro exitoso
   */
  async sendWelcomeEmail(user: User): Promise<boolean> {
    if (!this.enabled) {
      console.warn('Email service disabled');
      return false;
    }

    try {
      const html = `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="UTF-8">
            <style>
              body { font-family: Arial, sans-serif; color: #333; line-height: 1.6; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }
              .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
              .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
              .footer { font-size: 12px; color: #666; margin-top: 30px; text-align: center; border-top: 1px solid #ddd; padding-top: 20px; }
              .info { background: #e8f4f8; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0; }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>Bienvenido a GDPR Data Request</h1>
              </div>
              <div class="content">
                <p>Hola ${user.fullName},</p>

                <p>Tu cuenta ha sido creada exitosamente. Ahora puedes solicitar acceso a todos tus datos personales bajo el Artículo 15 del GDPR.</p>

                <div class="info">
                  <strong>¿Qué es esto?</strong><br>
                  Esta aplicación te permite solicitar que recopilemos todos tus datos personales en un archivo ZIP. Procesamos tu solicitud en máximo 30 días conforme a la ley europea.
                </div>

                <h3>Próximos pasos:</h3>
                <ol>
                  <li>Inicia sesión en la aplicación</li>
                  <li>Crea una nueva solicitud GDPR</li>
                  <li>Selecciona las categorías de datos que necesitas</li>
                  <li>Recibe tu archivo ZIP cuando esté listo</li>
                </ol>

                <a href="${process.env.FRONTEND_URL || 'https://gdpr-app.com'}" class="button">Ir a la aplicación</a>

                <div class="info">
                  <strong>Seguridad:</strong><br>
                  • Todos tus datos están encriptados (TLS)<br>
                  • Contraseña hasheada con PBKDF2<br>
                  • Auditoría completa de acceso<br>
                  • Cumplimiento GDPR garantizado
                </div>

                <p>Si tienes dudas, contáctanos: privacy@example.com</p>
              </div>
              <div class="footer">
                <p>© GDPR Data Request | Privacidad garantizada bajo GDPR Art. 15</p>
              </div>
            </div>
          </body>
        </html>
      `;

      await this.transporter.sendMail({
        from: this.config.from,
        to: user.email,
        subject: 'Bienvenido a GDPR Data Request',
        html,
        text: 'Bienvenido. Inicia sesión para crear tu primera solicitud GDPR.',
      });

      return true;
    } catch (error) {
      console.error(`Failed to send welcome email to ${user.email}:`, error);
      return false;
    }
  }

  /**
   * Envía notificación de restablecimiento de contraseña
   */
  async sendPasswordResetEmail(user: User, resetToken: string): Promise<boolean> {
    if (!this.enabled) {
      console.warn('Email service disabled');
      return false;
    }

    try {
      const resetLink = `${process.env.FRONTEND_URL || 'https://gdpr-app.com'}/reset-password?token=${resetToken}`;

      const html = `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="UTF-8">
            <style>
              body { font-family: Arial, sans-serif; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .alert { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }
              .button { display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; }
              .footer { font-size: 12px; color: #666; margin-top: 30px; }
            </style>
          </head>
          <body>
            <div class="container">
              <h2>Restablecimiento de contraseña</h2>

              <p>Hola ${user.fullName},</p>

              <p>Recibimos una solicitud para restablecer tu contraseña. Si no fuiste tú, ignora este email.</p>

              <div class="alert">
                <strong>⚠️ Este enlace expira en 1 hora</strong><br>
                No compartas este enlace con nadie.
              </div>

              <a href="${resetLink}" class="button">Restablecer contraseña</a>

              <p>O copia este enlace en tu navegador:</p>
              <p style="word-break: break-all; background: #f5f5f5; padding: 10px;">${resetLink}</p>

              <div class="footer">
                <p>© GDPR Data Request | Email de seguridad</p>
              </div>
            </div>
          </body>
        </html>
      `;

      await this.transporter.sendMail({
        from: this.config.from,
        to: user.email,
        subject: 'Restablecimiento de contraseña - GDPR Data Request',
        html,
        text: `Enlace de restablecimiento: ${resetLink}`,
      });

      return true;
    } catch (error) {
      console.error(`Failed to send password reset email to ${user.email}:`, error);
      return false;
    }
  }

  /**
   * Obtiene el asunto del email según el estado
   */
  private getSubjectForStatus(status: string): string {
    const subjects: Record<string, string> = {
      pending: '📧 Tu solicitud GDPR ha sido recibida',
      processing: '⏳ Tu solicitud está siendo procesada',
      ready: '📦 Tus datos están listos para descargar',
      completed: '✅ Tu solicitud ha sido completada',
      rejected: '❌ Tu solicitud no pudo ser procesada',
    };
    return subjects[status] || 'Actualización de solicitud GDPR';
  }

  /**
   * Genera el template HTML del email según estado
   */
  private getEmailTemplate(user: User, request: GDPRRequest, previousStatus: string): string {
    const baseStyles = `
      body { font-family: Arial, sans-serif; color: #333; line-height: 1.6; }
      .container { max-width: 600px; margin: 0 auto; padding: 20px; }
      .header { padding: 20px; text-align: center; border-bottom: 2px solid #667eea; }
      .content { padding: 30px; background: #f9f9f9; }
      .status-badge { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin: 10px 0; }
      .status-pending { background: #fff3cd; color: #856404; }
      .status-processing { background: #d1ecf1; color: #0c5460; }
      .status-ready { background: #d4edda; color: #155724; }
      .status-completed { background: #e7e7e7; color: #383d41; }
      .status-rejected { background: #f8d7da; color: #721c24; }
      .info-box { background: white; padding: 15px; border-left: 4px solid #667eea; margin: 15px 0; }
      .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; }
      .footer { font-size: 12px; color: #666; margin-top: 30px; text-align: center; }
    `;

    let statusMessage = '';
    switch (request.status) {
      case 'pending':
        statusMessage = `
          <p>Tu solicitud ha sido registrada en nuestro sistema.</p>
          <div class="info-box">
            <strong>ID de solicitud:</strong> ${request.id}<br>
            <strong>Categorías solicitadas:</strong> ${request.dataCategories.join(', ')}<br>
            <strong>Fecha vencimiento:</strong> ${new Date(request.expiresAt).toLocaleDateString('es-ES')}
          </div>
          <p>Procesaremos tu solicitud dentro de 30 días conforme a la ley GDPR.</p>
        `;
        break;

      case 'processing':
        statusMessage = `
          <p>¡Buenas noticias! Estamos recopilando y preparando tus datos.</p>
          <div class="info-box">
            <strong>Estado actual:</strong> Recopilando datos<br>
            <strong>Tiempo estimado:</strong> 5-10 días hábiles<br>
            <strong>Te notificaremos</strong> cuando el archivo esté listo.
          </div>
        `;
        break;

      case 'ready':
        statusMessage = `
          <p>¡Tu archivo está listo para descargar!</p>
          <div class="info-box">
            <strong>Formato:</strong> ZIP comprimido<br>
            <strong>Disponible por:</strong> 7 días<br>
            <strong>Vencimiento:</strong> ${new Date(new Date().getTime() + 7 * 24 * 60 * 60 * 1000).toLocaleDateString('es-ES')}
          </div>
          <p>Haz clic en el botón abajo para descargar.</p>
        `;
        break;

      case 'completed':
        statusMessage = `
          <p>Tu solicitud GDPR ha sido completada.</p>
          <div class="info-box">
            <strong>Completada el:</strong> ${request.completedAt ? new Date(request.completedAt).toLocaleDateString('es-ES') : 'Hoy'}<br>
            <strong>Archivos descargados:</strong> Sí<br>
            <strong>Estado:</strong> Archivado
          </div>
          <p>Si necesitas otra solicitud, puedes crear una nueva en cualquier momento.</p>
        `;
        break;

      case 'rejected':
        statusMessage = `
          <p>Desafortunadamente, no pudimos procesar tu solicitud.</p>
          <div class="info-box">
            <strong>Razón:</strong> ${request.notes || 'No especificada'}<br>
            <strong>Opciones:</strong><br>
            • Contacta con soporte: privacy@example.com<br>
            • Crea una nueva solicitud con información diferente
          </div>
        `;
        break;
    }

    return `
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="UTF-8">
          <style>${baseStyles}</style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>Actualización de solicitud GDPR</h1>
            </div>
            <div class="content">
              <p>Hola ${user.fullName},</p>

              <div class="status-badge status-${request.status}">
                ${this.getStatusLabel(request.status)}
              </div>

              ${statusMessage}

              ${request.status === 'ready' ? `<a href="${process.env.FRONTEND_URL || 'https://gdpr-app.com'}/requests/${request.id}" class="button">Descargar datos</a>` : ''}

              ${request.status !== 'rejected' && request.status !== 'completed' ? `
                <p style="margin-top: 30px;">
                  <a href="${process.env.FRONTEND_URL || 'https://gdpr-app.com'}/requests/${request.id}" style="color: #667eea; text-decoration: none;">
                    Ver detalles de la solicitud →
                  </a>
                </p>
              ` : ''}

              <div class="info-box">
                <strong>¿Preguntas?</strong><br>
                Contacta con nuestro equipo de privacidad: privacy@example.com<br>
                Disponible 24/7 bajo GDPR Art. 15
              </div>
            </div>
            <div class="footer">
              <p>© GDPR Data Request | Protección de datos garantizada</p>
              <p>Este es un email automático. No responds a esta dirección.</p>
            </div>
          </div>
        </body>
      </html>
    `;
  }

  /**
   * Obtiene la etiqueta de estado
   */
  private getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      processing: 'Procesando',
      ready: 'Listo para descargar',
      completed: 'Completado',
      rejected: 'Rechazado',
    };
    return labels[status] || status;
  }

  /**
   * Elimina tags HTML de un string
   */
  private stripHtml(html: string): string {
    return html.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
  }

  /**
   * Verifica si el servicio está habilitado
   */
  isEnabled(): boolean {
    return this.enabled;
  }
}

export default new EmailService();
