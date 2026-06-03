import pg from 'pg';
import { config } from 'dotenv';

config();

const { Pool } = pg;

/**
 * PostgreSQL connection pool
 * Reuses connections for better performance
 */
export const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20, // Maximum number of clients in the pool
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

/**
 * Health check for database connection
 */
export async function checkDatabaseHealth(): Promise<boolean> {
  try {
    const result = await pool.query('SELECT NOW()');
    console.log('[DB] Connection verified:', result.rows[0].now);
    return true;
  } catch (error) {
    console.error('[DB] Connection failed:', error);
    return false;
  }
}

/**
 * Initialize database schema
 * Creates tables if they don't exist
 */
export async function initializeDatabase(): Promise<void> {
  const client = await pool.connect();
  try {
    // Create requests table
    await client.query(`
      CREATE TABLE IF NOT EXISTS requests (
        id VARCHAR(50) PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL,
        full_name VARCHAR(255) NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'pending',
        data_categories TEXT[] NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        reason TEXT,
        data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        INDEX idx_user_id (user_id),
        INDEX idx_email (email),
        INDEX idx_status (status),
        INDEX idx_created_at (created_at)
      );
    `);

    // Create audit logs table
    await client.query(`
      CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        request_id VARCHAR(50),
        action VARCHAR(100) NOT NULL,
        actor VARCHAR(255) NOT NULL,
        details TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (request_id) REFERENCES requests(id),
        INDEX idx_request_id (request_id),
        INDEX idx_created_at (created_at)
      );
    `);

    // Create metrics table for SLA tracking
    await client.query(`
      CREATE TABLE IF NOT EXISTS metrics (
        id SERIAL PRIMARY KEY,
        request_id VARCHAR(50),
        metric_name VARCHAR(100) NOT NULL,
        metric_value NUMERIC(10, 2),
        recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (request_id) REFERENCES requests(id),
        INDEX idx_request_id (request_id),
        INDEX idx_metric_name (metric_name)
      );
    `);

    console.log('[DB] Schema initialized successfully');
  } catch (error) {
    console.error('[DB] Schema initialization failed:', error);
    throw error;
  } finally {
    client.release();
  }
}

/**
 * Close database connection pool
 */
export async function closeDatabase(): Promise<void> {
  await pool.end();
  console.log('[DB] Connection pool closed');
}
