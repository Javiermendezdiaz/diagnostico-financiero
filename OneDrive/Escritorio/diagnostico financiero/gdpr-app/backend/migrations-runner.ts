import fs from 'fs';
import path from 'path';
import { pool } from '../database';

/**
 * Database migration runner
 * Executes SQL migration files in order
 */

interface Migration {
  name: string;
  version: string;
  executed: boolean;
}

/**
 * Run all pending migrations
 */
export async function runMigrations(migrationsDir: string): Promise<void> {
  const client = await pool.connect();

  try {
    // Create migrations tracking table if it doesn't exist
    await client.query(`
      CREATE TABLE IF NOT EXISTS schema_migrations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
      );
    `);

    // Get list of applied migrations
    const appliedResult = await client.query(
      'SELECT name FROM schema_migrations ORDER BY executed_at;'
    );
    const appliedMigrations = new Set(appliedResult.rows.map((row) => row.name));

    // Get list of migration files
    const files = fs
      .readdirSync(migrationsDir)
      .filter((file) => file.endsWith('.sql'))
      .sort();

    console.log(`[MIGRATIONS] Found ${files.length} migration files`);

    let executedCount = 0;

    for (const file of files) {
      if (appliedMigrations.has(file)) {
        console.log(`[MIGRATIONS] Skipping ${file} (already applied)`);
        continue;
      }

      const filePath = path.join(migrationsDir, file);
      const sql = fs.readFileSync(filePath, 'utf-8');

      try {
        console.log(`[MIGRATIONS] Executing ${file}...`);
        await client.query(sql);

        // Record migration as executed
        await client.query(
          'INSERT INTO schema_migrations (name) VALUES ($1);',
          [file]
        );

        executedCount++;
        console.log(`[MIGRATIONS] ✓ ${file} completed`);
      } catch (error) {
        console.error(`[MIGRATIONS] ✗ ${file} failed:`, error);
        throw error;
      }
    }

    console.log(
      `[MIGRATIONS] Migration run complete. ${executedCount} new migrations executed.`
    );
  } finally {
    client.release();
  }
}

/**
 * Get migration status
 */
export async function getMigrationStatus(
  migrationsDir: string
): Promise<{ total: number; applied: number; pending: number }> {
  const client = await pool.connect();

  try {
    // Ensure migrations table exists
    await client.query(`
      CREATE TABLE IF NOT EXISTS schema_migrations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
      );
    `);

    // Get applied migrations
    const appliedResult = await client.query(
      'SELECT name FROM schema_migrations ORDER BY executed_at;'
    );
    const appliedMigrations = new Set(appliedResult.rows.map((row) => row.name));

    // Get all migration files
    const files = fs
      .readdirSync(migrationsDir)
      .filter((file) => file.endsWith('.sql'))
      .sort();

    const pendingCount = files.filter((file) => !appliedMigrations.has(file)).length;

    return {
      total: files.length,
      applied: appliedMigrations.size,
      pending: pendingCount,
    };
  } finally {
    client.release();
  }
}

/**
 * Rollback the last migration (use with caution!)
 */
export async function rollbackLastMigration(): Promise<string | null> {
  const client = await pool.connect();

  try {
    const result = await client.query(
      'SELECT name FROM schema_migrations ORDER BY executed_at DESC LIMIT 1;'
    );

    if (result.rows.length === 0) {
      console.log('[MIGRATIONS] No migrations to rollback');
      return null;
    }

    const migrationName = result.rows[0].name;
    console.warn(`[MIGRATIONS] WARNING: Attempting to rollback ${migrationName}`);
    console.warn('[MIGRATIONS] This operation should be done carefully and manually!');

    // Remove from tracking
    await client.query('DELETE FROM schema_migrations WHERE name = $1;', [
      migrationName,
    ]);

    console.log(`[MIGRATIONS] ✓ Rollback record removed for ${migrationName}`);
    return migrationName;
  } finally {
    client.release();
  }
}
