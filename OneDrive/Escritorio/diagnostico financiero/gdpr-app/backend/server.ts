import express, { Express, Request, Response, NextFunction } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import rateLimit from 'express-rate-limit';
import jwt from 'jsonwebtoken';
import {
  pool,
  initializeDatabase,
  closeDatabase,
  checkDatabaseHealth,
} from './database';
import { runMigrations } from './migrations-runner';
import { registerUser, authenticateUser } from './services-auth';
import { logAction, AuditActions } from './services-audit';
import emailService from './services-email';
import requestsRouter from './routes-requests-db';

// Load environment variables
dotenv.config();

const app: Express = express();
const PORT = parseInt(process.env.PORT || '3001', 10);
const NODE_ENV = process.env.NODE_ENV || 'development';

/**
 * Middleware Configuration
 */

// CORS Configuration
app.use(
  cors({
    origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
    credentials: true,
    methods: ['GET', 'POST', 'PATCH', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  })
);

// Body parser middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ limit: '10mb', extended: true }));

// Rate limiting
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000', 10), // 15 minutes
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100', 10),
  message: 'Too many requests from this IP, please try again later.',
  standardHeaders: true,
  legacyHeaders: false,
});

// Apply rate limiting to API routes
app.use('/api/', limiter);

/**
 * JWT Authentication Middleware
 */
const authenticateToken = (
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Extract token from "Bearer TOKEN"

  if (!token) {
    res.status(401).json({ error: 'Access token required' });
    return;
  }

  jwt.verify(
    token,
    process.env.JWT_SECRET || 'your-secret-key',
    (err: jwt.VerifyErrors | null, decoded: any) => {
      if (err) {
        return res.status(403).json({ error: 'Invalid or expired token' });
      }
      (req as any).userId = decoded.userId;
      next();
    }
  );
};

/**
 * Health Check Route
 */
app.get('/health', async (req: Request, res: Response) => {
  try {
    const dbHealth = await checkDatabaseHealth();
    res.json({
      status: 'ok',
      environment: NODE_ENV,
      timestamp: new Date().toISOString(),
      database: dbHealth,
    });
  } catch (error) {
    console.error('[Health Check] Error:', error);
    res.status(503).json({
      status: 'error',
      message: 'Health check failed',
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

/**
 * Authentication Routes (no JWT required)
 */

// POST /api/auth/register
app.post('/api/auth/register', async (req: Request, res: Response) => {
  try {
    const { email, password, fullName } = req.body;

    if (!email || !password || !fullName) {
      return res.status(400).json({
        error: 'Missing required fields: email, password, fullName',
      });
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.status(400).json({ error: 'Invalid email format' });
    }

    // Validate password strength
    if (password.length < 8) {
      return res.status(400).json({
        error: 'Password must be at least 8 characters',
      });
    }

    // Register user in database
    const user = await registerUser(email, password, fullName);

    // Send welcome email (non-blocking)
    emailService.sendWelcomeEmail(user).catch((error) => {
      console.warn(`[Email] Failed to send welcome email to ${user.email}:`, error);
    });

    // Generate JWT token
    const token = jwt.sign(
      { userId: user.id, email: user.email },
      process.env.JWT_SECRET || 'your-secret-key',
      { expiresIn: process.env.JWT_EXPIRATION || '7d' }
    );

    // Log audit trail
    await logAction(AuditActions.USER_AUTHENTICATED, user.id, '', {
      email: user.email,
      action: 'user_registered',
    });

    res.status(201).json({
      success: true,
      user: { id: user.id, email: user.email, fullName: user.fullName },
      token,
    });
  } catch (error) {
    console.error('[Auth] Register error:', error);
    const message =
      error instanceof Error ? error.message : 'Registration failed';
    res.status(400).json({ error: message });
  }
});

// POST /api/auth/login
app.post('/api/auth/login', async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        error: 'Missing required fields: email, password',
      });
    }

    // Authenticate user
    const user = await authenticateUser(email, password);

    if (!user) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    // Generate JWT token
    const token = jwt.sign(
      { userId: user.id, email: user.email },
      process.env.JWT_SECRET || 'your-secret-key',
      { expiresIn: process.env.JWT_EXPIRATION || '7d' }
    );

    // Log audit trail
    await logAction(AuditActions.USER_AUTHENTICATED, user.id, '', {
      email: user.email,
    });

    res.json({
      success: true,
      user: { id: user.id, email: user.email, fullName: user.fullName },
      token,
    });
  } catch (error) {
    console.error('[Auth] Login error:', error);
    res.status(500).json({ error: 'Login failed' });
  }
});

/**
 * Protected Routes (JWT required)
 */
app.use('/api/requests', authenticateToken);
app.use('/api/requests', requestsRouter);

/**
 * Error Handling Middleware
 */
app.use((err: any, req: Request, res: Response, next: NextFunction) => {
  console.error('[Error Handler]', err);

  const statusCode = err.statusCode || 500;
  const message = err.message || 'Internal server error';

  res.status(statusCode).json({
    error: message,
    ...(NODE_ENV === 'development' && { stack: err.stack }),
  });
});

/**
 * 404 Handler
 */
app.use((req: Request, res: Response) => {
  res.status(404).json({
    error: 'Not found',
    path: req.path,
  });
});

/**
 * Database Initialization & Server Startup
 */
const startServer = async () => {
  try {
    console.log(`[Server] Starting GDPR Data Request Application...`);
    console.log(`[Server] Environment: ${NODE_ENV}`);

    // Initialize database connection pool
    console.log('[Database] Initializing connection pool...');
    await initializeDatabase();
    console.log('[Database] Connection pool ready');

    // Run migrations
    console.log('[Migrations] Running migrations...');
    await runMigrations(path.join(__dirname, 'migrations'));
    console.log('[Migrations] All migrations completed successfully');

    // Start HTTP server
    app.listen(PORT, () => {
      console.log(`[Server] Running on http://localhost:${PORT}`);
      console.log(`[Server] Health check: http://localhost:${PORT}/health`);
      console.log('[Server] Ready to accept requests');
    });
  } catch (error) {
    console.error('[Server] Startup error:', error);
    process.exit(1);
  }
};

/**
 * Graceful Shutdown
 */
const handleShutdown = async (signal: string) => {
  console.log(`[Server] Received ${signal} signal, shutting down gracefully...`);
  try {
    await closeDatabase();
    console.log('[Database] Connection pool closed');
    process.exit(0);
  } catch (error) {
    console.error('[Shutdown] Error closing database:', error);
    process.exit(1);
  }
};

process.on('SIGTERM', () => handleShutdown('SIGTERM'));
process.on('SIGINT', () => handleShutdown('SIGINT'));

// Start the server
startServer();

export default app;
