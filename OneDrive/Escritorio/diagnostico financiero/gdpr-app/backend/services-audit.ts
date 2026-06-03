import { pool } from '../database';

/**
 * Audit logging service for GDPR compliance
 * Tracks all actions on data requests for accountability and compliance
 */

export interface AuditLog {
  id: number;
  requestId?: string;
  action: string;
  actor: string;
  details?: string;
  createdAt: Date;
}

/**
 * Log an action to the audit trail
 */
export async function logAction(
  action: string,
  actor: string,
  requestId?: string,
  details?: Record<string, unknown>
): Promise<number> {
  const query = `
    INSERT INTO audit_logs (request_id, action, actor, details, created_at)
    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
    RETURNING id;
  `;

  try {
    const result = await pool.query(query, [
      requestId || null,
      action,
      actor,
      details ? JSON.stringify(details) : null,
    ]);

    return result.rows[0].id;
  } catch (error) {
    console.error('[AUDIT] Error logging action:', error);
    throw error;
  }
}

/**
 * Get audit logs for a specific request
 */
export async function getRequestAuditLogs(requestId: string): Promise<AuditLog[]> {
  const query = `
    SELECT id, request_id, action, actor, details, created_at
    FROM audit_logs
    WHERE request_id = $1
    ORDER BY created_at DESC;
  `;

  try {
    const result = await pool.query(query, [requestId]);
    return result.rows.map((row) => ({
      id: row.id,
      requestId: row.request_id,
      action: row.action,
      actor: row.actor,
      details: row.details ? JSON.parse(row.details) : undefined,
      createdAt: new Date(row.created_at),
    }));
  } catch (error) {
    console.error('[AUDIT] Error fetching request audit logs:', error);
    throw error;
  }
}

/**
 * Get all audit logs within a date range
 */
export async function getAuditLogsByDateRange(
  startDate: Date,
  endDate: Date,
  action?: string
): Promise<AuditLog[]> {
  let query = `
    SELECT id, request_id, action, actor, details, created_at
    FROM audit_logs
    WHERE created_at BETWEEN $1 AND $2
  `;

  const params: unknown[] = [startDate, endDate];

  if (action) {
    query += ' AND action = $3';
    params.push(action);
  }

  query += ' ORDER BY created_at DESC;';

  try {
    const result = await pool.query(query, params);
    return result.rows.map((row) => ({
      id: row.id,
      requestId: row.request_id,
      action: row.action,
      actor: row.actor,
      details: row.details ? JSON.parse(row.details) : undefined,
      createdAt: new Date(row.created_at),
    }));
  } catch (error) {
    console.error('[AUDIT] Error fetching audit logs by date range:', error);
    throw error;
  }
}

/**
 * Get audit summary for compliance reporting
 */
export async function getAuditSummary(): Promise<Record<string, unknown>> {
  const query = `
    SELECT
      COUNT(*) as total_logs,
      COUNT(DISTINCT request_id) as requests_audited,
      COUNT(DISTINCT action) as unique_actions,
      COUNT(DISTINCT actor) as unique_actors,
      MAX(created_at) as last_log_time
    FROM audit_logs;
  `;

  try {
    const result = await pool.query(query);
    return result.rows[0];
  } catch (error) {
    console.error('[AUDIT] Error fetching audit summary:', error);
    throw error;
  }
}

/**
 * Standard audit actions for tracking
 */
export const AuditActions = {
  REQUEST_CREATED: 'REQUEST_CREATED',
  REQUEST_SUBMITTED: 'REQUEST_SUBMITTED',
  REQUEST_ACCEPTED: 'REQUEST_ACCEPTED',
  REQUEST_PROCESSING: 'REQUEST_PROCESSING',
  REQUEST_COMPLETED: 'REQUEST_COMPLETED',
  REQUEST_FAILED: 'REQUEST_FAILED',
  REQUEST_CANCELLED: 'REQUEST_CANCELLED',
  DATA_ACCESSED: 'DATA_ACCESSED',
  DATA_DOWNLOADED: 'DATA_DOWNLOADED',
  DATA_DELETED: 'DATA_DELETED',
  USER_AUTHENTICATED: 'USER_AUTHENTICATED',
  USER_LOGOUT: 'USER_LOGOUT',
} as const;
