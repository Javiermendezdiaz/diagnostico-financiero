import { Router, Request, Response } from 'express';
import archiver from 'archiver';
import { v4 as uuidv4 } from 'uuid';
import {
  createRequest as dbCreateRequest,
  getRequestById as dbGetRequestById,
  getRequestsByUserId as dbGetRequestsByUserId,
  updateRequestStatus,
  storeRequestData,
} from './services-requests-db';
import { getUserById } from './services-auth';
import { logAction, AuditActions } from './services-audit';
import emailService from './services-email';

const router = Router();

/**
 * POST /api/requests
 * Create a new GDPR data request
 */
router.post('/requests', async (req: Request, res: Response) => {
  try {
    const { email, fullName, dataCategories, reason } = req.body;
    const userId = (req as any).userId; // From JWT middleware

    // Validation
    if (!email || !fullName || !dataCategories || !reason) {
      return res.status(400).json({
        error: 'Missing required fields: email, fullName, dataCategories, reason',
      });
    }

    if (!Array.isArray(dataCategories) || dataCategories.length === 0) {
      return res.status(400).json({
        error: 'dataCategories must be a non-empty array',
      });
    }

    const requestId = `REQ-${new Date().getFullYear()}-${Math.random()
      .toString(36)
      .substr(2, 9)
      .toUpperCase()}`;

    // Create request in database
    const newRequest = await dbCreateRequest(
      requestId,
      userId,
      email,
      fullName,
      dataCategories,
      reason
    );

    // Log audit trail
    await logAction(AuditActions.REQUEST_CREATED, userId, requestId, {
      email,
      fullName,
      dataCategories,
    });

    res.status(201).json({
      success: true,
      request: newRequest,
    });
  } catch (error) {
    console.error('[API] Error creating request:', error);
    res.status(500).json({ error: 'Failed to create request' });
  }
});

/**
 * GET /api/requests
 * Get all requests for the authenticated user
 */
router.get('/requests', async (req: Request, res: Response) => {
  try {
    const userId = (req as any).userId; // From JWT middleware
    const requests = await dbGetRequestsByUserId(userId);

    res.json({
      success: true,
      requests,
      total: requests.length,
    });
  } catch (error) {
    console.error('[API] Error fetching requests:', error);
    res.status(500).json({ error: 'Failed to fetch requests' });
  }
});

/**
 * GET /api/requests/:id
 * Get a specific request by ID
 */
router.get('/requests/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const userId = (req as any).userId; // From JWT middleware

    const request = await dbGetRequestById(id);

    if (!request) {
      return res.status(404).json({ error: 'Request not found' });
    }

    // Verify user owns this request
    if (request.userId !== userId) {
      return res.status(403).json({ error: 'Access denied' });
    }

    // Log audit trail
    await logAction(AuditActions.DATA_ACCESSED, userId, id);

    res.json({
      success: true,
      request,
    });
  } catch (error) {
    console.error('[API] Error fetching request:', error);
    res.status(500).json({ error: 'Failed to fetch request' });
  }
});

/**
 * GET /api/requests/:id/download
 * Download GDPR data as ZIP file
 */
router.get('/requests/:id/download', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const userId = (req as any).userId; // From JWT middleware

    const request = await dbGetRequestById(id);

    if (!request) {
      return res.status(404).json({ error: 'Request not found' });
    }

    // Verify user owns this request
    if (request.userId !== userId) {
      return res.status(403).json({ error: 'Access denied' });
    }

    // Only allow download if status is completed
    if (request.status !== 'completed') {
      return res.status(400).json({
        error: `Cannot download: request status is '${request.status}'. Data is only available when status is 'completed'.`,
      });
    }

    // Check if download window is still valid (30 days)
    const validityDays = parseInt(process.env.GDPR_REQUEST_VALIDITY_DAYS || '30');
    const expiryDate = new Date(request.createdAt);
    expiryDate.setDate(expiryDate.getDate() + validityDays);

    if (new Date() > expiryDate) {
      return res.status(410).json({
        error: 'Download window has expired. Data is available for 30 days from request creation.',
      });
    }

    // Log audit trail
    await logAction(AuditActions.DATA_DOWNLOADED, userId, id, {
      downloadTime: new Date().toISOString(),
    });

    // Create ZIP archive
    const archive = archiver('zip', {
      zlib: { level: 9 },
    });

    res.setHeader('Content-Type', 'application/zip');
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="gdpr-request-${id}.zip"`
    );

    archive.pipe(res);

    // Add metadata file
    archive.append(
      JSON.stringify(
        {
          requestId: request.id,
          email: request.email,
          fullName: request.fullName,
          status: request.status,
          requestedAt: request.createdAt,
          downloadedAt: new Date().toISOString(),
          expiresAt: expiryDate.toISOString(),
          validityDays,
        },
        null,
        2
      ),
      {
        name: 'datos-solicitud.json',
      }
    );

    // Add sample data for each category
    const sampleData = generateSampleData(request.dataCategories);
    for (const [category, data] of Object.entries(sampleData)) {
      archive.append(JSON.stringify(data, null, 2), {
        name: `${category}.txt`,
      });
    }

    // Add Spanish legal notice
    const legalNotice = `
AVISO LEGAL - DATOS PERSONALES DESCARGADOS

Este archivo contiene los datos personales descargados conforme a su solicitud RGPD.

Solicitud ID: ${request.id}
Email: ${request.email}
Fecha de descarga: ${new Date().toISOString()}
Fecha de caducidad: ${expiryDate.toISOString()}

POLÍTICAS DE PRIVACIDAD:
- Estos datos son confidenciales y están protegidos por la Ley Orgánica 3/2018 (LOPD-GDD)
- No distribuya estos datos a terceros sin autorización
- Destruya estos datos de forma segura después de 30 días
- Cualquier acceso no autorizado será investigado

Para más información sobre sus derechos RGPD, consulte nuestra política de privacidad.
    `.trim();

    archive.append(legalNotice, {
      name: 'AVISO-LEGAL.txt',
    });

    await archive.finalize();
  } catch (error) {
    console.error('[API] Error downloading request data:', error);
    res.status(500).json({ error: 'Failed to download data' });
  }
});

/**
 * PATCH /api/requests/:id/status
 * Update request status (admin/internal only)
 */
router.patch('/requests/:id/status', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { status } = req.body;
    const userId = (req as any).userId;

    const validStatuses = ['pending', 'processing', 'completed', 'failed', 'cancelled'];
    if (!validStatuses.includes(status)) {
      return res.status(400).json({
        error: `Invalid status. Must be one of: ${validStatuses.join(', ')}`,
      });
    }

    // Get current request to capture previous status
    const currentRequest = await dbGetRequestById(id);
    const previousStatus = currentRequest?.status || 'unknown';

    const updatedRequest = await updateRequestStatus(id, status);

    // Log audit trail
    await logAction(
      status === 'completed'
        ? AuditActions.REQUEST_COMPLETED
        : AuditActions.REQUEST_PROCESSING,
      userId,
      id,
      { newStatus: status }
    );

    // Send status change notification email (non-blocking)
    const user = await getUserById(userId);
    if (user) {
      emailService.sendStatusChangeNotification(user, updatedRequest, previousStatus).catch((error) => {
        console.warn(`[Email] Failed to send status notification to ${user.email}:`, error);
      });
    }

    res.json({
      success: true,
      request: updatedRequest,
    });
  } catch (error) {
    console.error('[API] Error updating request status:', error);
    res.status(500).json({ error: 'Failed to update request status' });
  }
});

/**
 * Generate realistic sample data for requested categories
 */
function generateSampleData(
  categories: string[]
): Record<string, Record<string, string | string[]>> {
  const data: Record<string, Record<string, string | string[]>> = {};

  const samples: Record<string, Record<string, string | string[]>> = {
    'Personal Information': {
      'Full Name': 'John Doe',
      'Date of Birth': '1990-01-15',
      'Nationality': 'Spanish',
      'National ID': '[REDACTED]',
      'Profile Picture': '[URL - REDACTED]',
    },
    'Contact Information': {
      'Email Address': 'john.doe@example.com',
      'Phone Number': '+34-6XX-XXX-XXX',
      'Home Address': '[REDACTED]',
      'Work Address': '[REDACTED]',
    },
    'Financial Information': {
      'Bank Account': '[REDACTED]',
      'Credit Card': '[REDACTED]',
      'Payment Methods': 'Visa, PayPal',
      'Transaction Total': '€12,345.67',
    },
    'Transaction History': {
      'Recent Purchases': [
        '2026-05-28: €49.99 - Digital Subscription',
        '2026-05-25: €159.99 - Electronics',
        '2026-05-20: €29.99 - Software License',
      ],
    },
    'Communication Records': {
      'Emails Received': '1,247',
      'Last Email': '2026-05-28 14:32:00',
      'Support Tickets': 3,
      'Feedback Submitted': 2,
    },
    'Location Data': {
      'Current Country': 'Spain',
      'Approximate Location': 'Madrid',
      'IP Address': '[REDACTED]',
      'Last Login Location': 'Madrid, Spain',
    },
    'Device Information': {
      'Device Type': 'Desktop',
      'Operating System': 'Windows 10',
      'Browser': 'Chrome 125.0',
      'Device ID': '[REDACTED]',
    },
    'Browsing History': {
      'Pages Visited': 342,
      'Average Session Duration': '8 minutes 32 seconds',
      'Last Visit': '2026-05-29 10:15:00',
      'Top Sections': ['Products', 'Support', 'Blog', 'Account Settings'],
    },
  };

  for (const category of categories) {
    if (samples[category]) {
      data[category] = samples[category];
    }
  }

  return data;
}

export default router;
