import { pool } from '../database';
import { DataRequest, DataCategory } from '../types';

/**
 * Database service for GDPR requests
 * Handles all request CRUD operations
 */

/**
 * Create a new GDPR data request
 */
export async function createRequest(
  id: string,
  userId: string,
  email: string,
  fullName: string,
  dataCategories: string[],
  reason: string
): Promise<DataRequest> {
  const query = `
    INSERT INTO requests (
      id, user_id, email, full_name, status, data_categories, reason, created_at, updated_at
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    RETURNING *;
  `;

  try {
    const result = await pool.query(query, [
      id,
      userId,
      email,
      fullName,
      'pending',
      dataCategories,
      reason,
    ]);

    const row = result.rows[0];
    return mapRowToRequest(row);
  } catch (error) {
    console.error('[DB] Error creating request:', error);
    throw error;
  }
}

/**
 * Get request by ID
 */
export async function getRequestById(id: string): Promise<DataRequest | null> {
  const query = 'SELECT * FROM requests WHERE id = $1;';

  try {
    const result = await pool.query(query, [id]);

    if (result.rows.length === 0) {
      return null;
    }

    return mapRowToRequest(result.rows[0]);
  } catch (error) {
    console.error('[DB] Error fetching request:', error);
    throw error;
  }
}

/**
 * Get all requests for a user
 */
export async function getRequestsByUserId(userId: string): Promise<DataRequest[]> {
  const query = `
    SELECT * FROM requests
    WHERE user_id = $1
    ORDER BY created_at DESC;
  `;

  try {
    const result = await pool.query(query, [userId]);
    return result.rows.map(mapRowToRequest);
  } catch (error) {
    console.error('[DB] Error fetching user requests:', error);
    throw error;
  }
}

/**
 * Update request status
 */
export async function updateRequestStatus(
  id: string,
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
): Promise<DataRequest> {
  const query = `
    UPDATE requests
    SET status = $1, updated_at = CURRENT_TIMESTAMP
    ${status === 'completed' ? ', completed_at = CURRENT_TIMESTAMP' : ''}
    WHERE id = $2
    RETURNING *;
  `;

  try {
    const result = await pool.query(query, [status, id]);

    if (result.rows.length === 0) {
      throw new Error(`Request ${id} not found`);
    }

    return mapRowToRequest(result.rows[0]);
  } catch (error) {
    console.error('[DB] Error updating request status:', error);
    throw error;
  }
}

/**
 * Store request data (ZIP contents metadata)
 */
export async function storeRequestData(id: string, data: Record<string, unknown>): Promise<void> {
  const query = `
    UPDATE requests
    SET data_json = $1, updated_at = CURRENT_TIMESTAMP
    WHERE id = $2;
  `;

  try {
    await pool.query(query, [JSON.stringify(data), id]);
  } catch (error) {
    console.error('[DB] Error storing request data:', error);
    throw error;
  }
}

/**
 * Get requests expiring soon (within N days)
 */
export async function getExpiringRequests(daysUntilExpiry: number): Promise<DataRequest[]> {
  const query = `
    SELECT * FROM requests
    WHERE status = 'completed'
    AND created_at > CURRENT_TIMESTAMP - INTERVAL '${daysUntilExpiry} days'
    ORDER BY created_at DESC;
  `;

  try {
    const result = await pool.query(query);
    return result.rows.map(mapRowToRequest);
  } catch (error) {
    console.error('[DB] Error fetching expiring requests:', error);
    throw error;
  }
}

/**
 * Delete request and associated data
 */
export async function deleteRequest(id: string): Promise<boolean> {
  const query = 'DELETE FROM requests WHERE id = $1;';

  try {
    const result = await pool.query(query, [id]);
    return result.rowCount! > 0;
  } catch (error) {
    console.error('[DB] Error deleting request:', error);
    throw error;
  }
}

/**
 * Get metrics for SLA compliance
 */
export async function getMetrics(days: number = 30): Promise<Record<string, unknown>> {
  const query = `
    SELECT
      COUNT(*) as total_requests,
      COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_requests,
      COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_requests,
      COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_requests,
      COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_requests,
      AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600) as avg_completion_hours,
      MAX(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600) as max_completion_hours
    FROM requests
    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '${days} days';
  `;

  try {
    const result = await pool.query(query);
    return result.rows[0];
  } catch (error) {
    console.error('[DB] Error fetching metrics:', error);
    throw error;
  }
}

/**
 * Map database row to DataRequest object
 */
function mapRowToRequest(row: Record<string, unknown>): DataRequest {
  return {
    id: row.id as string,
    userId: row.user_id as string,
    email: row.email as string,
    fullName: row.full_name as string,
    status: row.status as 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled',
    dataCategories: row.data_categories as string[],
    createdAt: new Date(row.created_at as string),
    updatedAt: new Date(row.updated_at as string),
    completedAt: row.completed_at ? new Date(row.completed_at as string) : undefined,
    reason: row.reason as string,
  };
}
