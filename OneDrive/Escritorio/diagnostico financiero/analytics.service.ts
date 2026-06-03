/**
 * Analytics Service — Fase 3: Enhanced UX
 * Tracking de eventos GDPR requests
 *
 * Events:
 * - request_created: Nueva solicitud creada (type: access/deletion/portability)
 * - request_completed: Solicitud completada exitosamente
 * - export_downloaded: Usuario descargó export
 * - request_cancelled: Usuario canceló solicitud
 * - request_failed: Solicitud rechazada por backend
 * - error_occurred: Error durante cualquier operación
 */

export interface AnalyticsEvent {
  event_name: string;
  timestamp: string;
  request_id?: string;
  request_type?: 'access' | 'deletion' | 'portability';
  status?: string;
  filename?: string;
  error_code?: string;
  error_message?: string;
  metadata?: Record<string, any>;
}

class AnalyticsService {
  private endpoint = '/api/v1/analytics/events';
  private queue: AnalyticsEvent[] = [];
  private batchSize = 10;
  private flushInterval = 30000; // 30s
  private flushIntervalId: NodeJS.Timeout | null = null;

  constructor() {
    // Flush queue on page unload
    window.addEventListener('beforeunload', () => this.flush());
    // Start auto-flush interval
    this.startAutoFlush();
  }

  /**
   * Track request creation
   */
  trackRequestCreated(requestId: string, type: 'access' | 'deletion' | 'portability') {
    this.track({
      event_name: 'request_created',
      request_id: requestId,
      request_type: type,
      metadata: { action: 'gdpr_request_initiated' },
    });
  }

  /**
   * Track request completion
   */
  trackRequestCompleted(requestId: string, type: string) {
    this.track({
      event_name: 'request_completed',
      request_id: requestId,
      request_type: type as any,
      metadata: { action: 'gdpr_request_fulfilled' },
    });
  }

  /**
   * Track export download
   */
  trackExportDownloaded(requestId: string, filename: string, sizeBytes?: number) {
    this.track({
      event_name: 'export_downloaded',
      request_id: requestId,
      filename,
      metadata: { size_bytes: sizeBytes, action: 'data_export_downloaded' },
    });
  }

  /**
   * Track request cancellation
   */
  trackRequestCancelled(requestId: string) {
    this.track({
      event_name: 'request_cancelled',
      request_id: requestId,
      metadata: { action: 'gdpr_request_cancelled' },
    });
  }

  /**
   * Track request rejection
   */
  trackRequestFailed(requestId: string, reason?: string) {
    this.track({
      event_name: 'request_failed',
      request_id: requestId,
      status: 'rejected',
      metadata: { reason, action: 'gdpr_request_rejected' },
    });
  }

  /**
   * Track errors
   */
  trackError(code: string, message: string, context?: Record<string, any>) {
    this.track({
      event_name: 'error_occurred',
      error_code: code,
      error_message: message,
      metadata: { ...context, action: 'error_tracked' },
    });
  }

  /**
   * Generic track method
   */
  private track(event: Omit<AnalyticsEvent, 'timestamp'>) {
    const analyticsEvent: AnalyticsEvent = {
      ...event,
      timestamp: new Date().toISOString(),
    };

    this.queue.push(analyticsEvent);

    // Flush if batch size reached
    if (this.queue.length >= this.batchSize) {
      this.flush();
    }
  }

  /**
   * Auto-flush interval
   */
  private startAutoFlush() {
    this.flushIntervalId = setInterval(() => {
      if (this.queue.length > 0) {
        this.flush();
      }
    }, this.flushInterval);
  }

  /**
   * Stop auto-flush
   */
  stopAutoFlush() {
    if (this.flushIntervalId) {
      clearInterval(this.flushIntervalId);
      this.flushIntervalId = null;
    }
  }

  /**
   * Flush queue to backend
   */
  async flush() {
    if (this.queue.length === 0) return;

    const events = [...this.queue];
    this.queue = [];

    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        // No token, queue events silently
        console.warn('[Analytics] No auth token, queueing events');
        this.queue.unshift(...events);
        return;
      }

      const response = await fetch(this.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ events }),
      });

      if (!response.ok) {
        // Requeue on failure
        console.error('[Analytics] Flush failed:', response.status);
        this.queue.unshift(...events);
      }
    } catch (err) {
      // Network error, requeue
      console.error('[Analytics] Flush error:', err);
      this.queue.unshift(...events);
    }
  }

  /**
   * Get current queue size
   */
  getQueueSize(): number {
    return this.queue.length;
  }

  /**
   * Clear queue
   */
  clearQueue() {
    this.queue = [];
  }
}

// Singleton instance
export const analytics = new AnalyticsService();
