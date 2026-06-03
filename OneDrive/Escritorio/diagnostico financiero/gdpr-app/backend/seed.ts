/**
 * Database seeding script
 * Populates test users for E2E testing
 *
 * Usage: npx ts-node backend/seed.ts
 */

import { pool } from './database';
import { hashPassword } from './services-auth';

interface TestUser {
  id: string;
  email: string;
  password: string;
  fullName: string;
  isAdmin: boolean;
}

const TEST_USERS: TestUser[] = [
  {
    id: 'user_001',
    email: 'user@example.com',
    password: 'TestPassword123!',
    fullName: 'Test User',
    isAdmin: false,
  },
  {
    id: 'admin_001',
    email: 'admin@example.com',
    password: 'AdminPassword123!',
    fullName: 'Admin User',
    isAdmin: true,
  },
  {
    id: 'user_002',
    email: 'john.doe@example.com',
    password: 'JohnPassword123!',
    fullName: 'John Doe',
    isAdmin: false,
  },
];

/**
 * Seed database with test users
 */
async function seedDatabase(): Promise<void> {
  const client = await pool.connect();

  try {
    console.log('[Seed] Starting database seeding...');

    // Check if users table exists
    const tableExists = await client.query(`
      SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'users'
      );
    `);

    if (!tableExists.rows[0].exists) {
      console.error('[Seed] ERROR: users table does not exist. Run migrations first.');
      process.exit(1);
    }

    // Clear existing test users
    const testEmails = TEST_USERS.map(u => u.email);
    await client.query(
      `DELETE FROM users WHERE email = ANY($1)`,
      [testEmails]
    );
    console.log('[Seed] Cleared existing test users');

    // Insert test users
    for (const user of TEST_USERS) {
      const passwordHash = hashPassword(user.password);

      await client.query(
        `INSERT INTO users (id, email, password_hash, full_name, is_active, created_at, updated_at)
         VALUES ($1, $2, $3, $4, $5, NOW(), NOW())`,
        [user.id, user.email, passwordHash, user.fullName, true]
      );

      console.log(`[Seed] Created user: ${user.email}`);
    }

    console.log('[Seed] Database seeding completed successfully');
    console.log('\n[Seed] Test credentials:');
    TEST_USERS.forEach(user => {
      console.log(`  Email: ${user.email}`);
      console.log(`  Password: ${user.password}`);
      console.log(`  Role: ${user.isAdmin ? 'Admin' : 'User'}`);
      console.log();
    });

  } catch (error) {
    console.error('[Seed] Error during seeding:', error);
    process.exit(1);
  } finally {
    await client.release();
    await pool.end();
    process.exit(0);
  }
}

// Run seeding
seedDatabase();
