import crypto from 'crypto';
import { pool } from './database';

/**
 * Hash a password using PBKDF2
 */
export function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto
    .pbkdf2Sync(password, salt, 100000, 64, 'sha512')
    .toString('hex');
  return `${salt}:${hash}`;
}

/**
 * Verify a password against a stored hash
 */
export function verifyPassword(password: string, storedHash: string): boolean {
  const [salt, hash] = storedHash.split(':');
  if (!salt || !hash) return false;

  const verifyHash = crypto
    .pbkdf2Sync(password, salt, 100000, 64, 'sha512')
    .toString('hex');
  return verifyHash === hash;
}

/**
 * Register a new user
 */
export async function registerUser(
  email: string,
  password: string,
  fullName: string
): Promise<{
  id: string;
  email: string;
  fullName: string;
  createdAt: string;
}> {
  try {
    // Check if user already exists
    const existingUser = await pool.query(
      'SELECT id FROM users WHERE email = $1',
      [email]
    );

    if (existingUser.rows.length > 0) {
      throw new Error('User already exists');
    }

    // Hash password
    const passwordHash = hashPassword(password);

    // Create new user
    const result = await pool.query(
      `INSERT INTO users (id, email, password_hash, full_name, is_active, created_at, updated_at)
       VALUES ($1, $2, $3, $4, true, NOW(), NOW())
       RETURNING id, email, full_name, created_at`,
      [`user-${Date.now()}`, email, passwordHash, fullName]
    );

    const user = result.rows[0];
    return {
      id: user.id,
      email: user.email,
      fullName: user.full_name,
      createdAt: user.created_at,
    };
  } catch (error) {
    console.error('[Auth] Registration error:', error);
    throw error;
  }
}

/**
 * Authenticate user by email and password
 */
export async function authenticateUser(
  email: string,
  password: string
): Promise<{ id: string; email: string; fullName: string } | null> {
  try {
    const result = await pool.query(
      'SELECT id, email, password_hash, full_name FROM users WHERE email = $1 AND is_active = true',
      [email]
    );

    if (result.rows.length === 0) {
      return null; // User not found
    }

    const user = result.rows[0];

    // Verify password
    if (!verifyPassword(password, user.password_hash)) {
      return null; // Invalid password
    }

    return {
      id: user.id,
      email: user.email,
      fullName: user.full_name,
    };
  } catch (error) {
    console.error('[Auth] Authentication error:', error);
    throw error;
  }
}

/**
 * Get user by ID
 */
export async function getUserById(userId: string): Promise<{
  id: string;
  email: string;
  fullName: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
} | null> {
  try {
    const result = await pool.query(
      'SELECT id, email, full_name, is_active, created_at, updated_at FROM users WHERE id = $1',
      [userId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const user = result.rows[0];
    return {
      id: user.id,
      email: user.email,
      fullName: user.full_name,
      isActive: user.is_active,
      createdAt: user.created_at,
      updatedAt: user.updated_at,
    };
  } catch (error) {
    console.error('[Auth] Get user error:', error);
    throw error;
  }
}

/**
 * Update user password
 */
export async function updateUserPassword(
  userId: string,
  newPassword: string
): Promise<boolean> {
  try {
    const passwordHash = hashPassword(newPassword);

    const result = await pool.query(
      'UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2',
      [passwordHash, userId]
    );

    return result.rowCount === 1;
  } catch (error) {
    console.error('[Auth] Update password error:', error);
    throw error;
  }
}

/**
 * Deactivate user account
 */
export async function deactivateUser(userId: string): Promise<boolean> {
  try {
    const result = await pool.query(
      'UPDATE users SET is_active = false, updated_at = NOW() WHERE id = $1',
      [userId]
    );

    return result.rowCount === 1;
  } catch (error) {
    console.error('[Auth] Deactivate user error:', error);
    throw error;
  }
}
