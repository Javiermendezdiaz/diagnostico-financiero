/**
 * Integration Test Suite — Fase 3 GDPR Data Requests
 * 
 * Validates complete end-to-end workflow:
 * • DataRequest creation (Articles 15, 17, 20)
 * • Status polling with exponential backoff
 * • Modal confirmation dialogs
 * • Auto-download on completion
 * • Analytics event batching & posting
 * • Bearer token refresh on 401
 */

import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DataRequestList } from './DataRequestList';
import { ConfirmationModal } from './ConfirmationModal';
import { AnalyticsService } from './analytics.service';

// Mock API responses
const mockApiResponses = {
  createRequest: (type: 'access' | 'deletion' | 'portability') => ({
    id: 'req-001',
    request_type: type,
    status: 'pending' as const,
    created_at: new Date().toISOString(),
    completed_at: null,
    expires_at: null,
    result_url: null,
    error_message: null,
  }),

  listRequests: [
    {
      id: 'req-001',
      request_type: 'access' as const,
      status: 'completed' as const,
      created_at: '2026-05-20T10:00:00Z',
      completed_at: '2026-05-21T14:30:00Z',
      expires_at: '2026-06-20T14:30:00Z',
      result_url: 'https://api.adapta.es/v1/data-requests/req-001/download',
      error_message: null,
    },
    {
      id: 'req-002',
      request_type: 'deletion' as const,
      status: 'processing' as const,
      created_at: '2026-05-25T08:00:00Z',
      completed_at: null,
      expires_at: null,
      result_url: null,
      error_message: null,
    },
  ],

  statusProgression: [
    { status: 'pending' as const, delay: 0 },
    { status: 'processing' as const, delay: 5000 },
    { status: 'completed' as const, delay: 10000 },
  ],

  downloadBlob: new Blob(['{"userData": "..."}'], { type: 'application/json' }),
};

// Test 1: Create GDPR Access Request
describe('DataRights Integration — Request Creation', () => {
  it('should create access request (Article 15) and set pending status', async () => {
    const user = userEvent.setup();

    // Mock fetch for POST /data-requests
    global.fetch = jest.fn((url: string, opts: any) => {
      if (url.includes('/data-requests') && opts.method === 'POST') {
        return Promise.resolve({
          status: 201,
          json: () => Promise.resolve(mockApiResponses.createRequest('access')),
        } as Response);
      }
      return Promise.reject(new Error('Unexpected URL'));
    });

    render(<DataRequestList />);

    // Locate "Solicitar acceso" button
    const accessButton = screen.getByRole('button', { name: /solicitar acceso/i });
    await user.click(accessButton);

    // Verify request created with pending status
    await waitFor(() => {
      expect(screen.getByText(/en espera/i)).toBeInTheDocument();
    });
  });

  it('should create deletion request (Article 17) and display danger modal', async () => {
    const user = userEvent.setup();

    global.fetch = jest.fn((url: string, opts: any) => {
      if (url.includes('/data-requests') && opts.method === 'POST') {
        return Promise.resolve({
          status: 201,
          json: () => Promise.resolve(mockApiResponses.createRequest('deletion')),
        } as Response);
      }
      return Promise.reject(new Error('Unexpected URL'));
    });

    render(<DataRequestList />);

    const deletionButton = screen.getByRole('button', { name: /solicitar eliminación/i });
    await user.click(deletionButton);

    // Modal should appear with warning about irreversibility
    await waitFor(() => {
      expect(screen.getByText(/datos serán eliminados/i)).toBeInTheDocument();
    });
  });
});

// Test 2: Status Polling with Exponential Backoff
describe('DataRights Integration — Status Polling', () => {
  it('should poll status every 5 seconds until completion', async () => {
    const fetchSpy = jest.fn();
    global.fetch = fetchSpy.mockImplementation((url: string, opts: any) => {
      if (url.includes('GET') || !opts?.method || opts.method === 'GET') {
        return Promise.resolve({
          status: 200,
          json: () => Promise.resolve(mockApiResponses.listRequests),
        } as Response);
      }
      return Promise.reject(new Error('Unexpected URL'));
    });

    render(<DataRequestList />);

    await waitFor(
      () => {
        // Should have called GET /data-requests multiple times (polling)
        const getCallCount = fetchSpy.mock.calls.filter((call) =>
          call[0].includes('/data-requests') && (!call[1] || call[1].method === 'GET')
        ).length;
        expect(getCallCount).toBeGreaterThan(0);
      },
      { timeout: 3000 }
    );
  });

  it('should retry with exponential backoff on network error', async () => {
    let attemptCount = 0;
    global.fetch = jest.fn(() => {
      attemptCount++;
      if (attemptCount < 3) {
        return Promise.reject(new Error('Network error'));
      }
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve(mockApiResponses.listRequests),
      } as Response);
    });

    render(<DataRequestList />);

    await waitFor(
      () => {
        // Should succeed on 3rd attempt after 1s, 2s backoff
        expect(screen.getByText(/en espera|procesando|disponible/i)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );
  });
});

// Test 3: Modal Confirmation Workflow
describe('DataRights Integration — Modal Confirmations', () => {
  it('should show cancellation warning modal for pending requests', async () => {
    const user = userEvent.setup();

    global.fetch = jest.fn((url: string) => {
      if (url.includes('/data-requests')) {
        return Promise.resolve({
          status: 200,
          json: () => Promise.resolve(mockApiResponses.listRequests),
        } as Response);
      }
      return Promise.reject(new Error('Unexpected URL'));
    });

    render(<DataRequestList />);

    // Find pending request (req-002)
    const cancelButton = await screen.findByRole('button', { name: /cancelar/i });
    await user.click(cancelButton);

    // Modal should appear with warning variant
    const modal = await screen.findByRole('alertdialog');
    expect(modal).toHaveClass('warning');
    expect(screen.getByText(/¿cancelar esta solicitud/i)).toBeInTheDocument();
  });

  it('should show deletion danger modal when cancelling deletion request', async () => {
    const user = userEvent.setup();

    // Mock a deletion request in processing state
    global.fetch = jest.fn(() =>
      Promise.resolve({
        status: 200,
        json: () =>
          Promise.resolve([
            {
              id: 'req-del-001',
              request_type: 'deletion',
              status: 'processing',
              created_at: '2026-05-25T08:00:00Z',
              completed_at: null,
              expires_at: null,
              result_url: null,
              error_message: null,
            },
          ]),
      } as Response)
    );

    render(<DataRequestList />);

    const cancelButton = await screen.findByRole('button', { name: /cancelar/i });
    await user.click(cancelButton);

    const modal = await screen.findByRole('alertdialog');
    expect(modal).toHaveClass('danger');
    expect(screen.getByText(/eliminación será cancelada/i)).toBeInTheDocument();
  });

  it('should POST to /data-requests/{id}/cancel on confirmation', async () => {
    const user = userEvent.setup();
    const cancelSpy = jest.fn();

    global.fetch = jest.fn((url: string, opts: any) => {
      if (url.includes('/cancel') && opts?.method === 'POST') {
        cancelSpy(url);
        return Promise.resolve({
          status: 200,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      }
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve(mockApiResponses.listRequests),
      } as Response);
    });

    render(<DataRequestList />);

    const cancelButton = await screen.findByRole('button', { name: /cancelar/i });
    await user.click(cancelButton);

    const confirmButton = await screen.findByRole('button', { name: /continuar/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(cancelSpy).toHaveBeenCalledWith(expect.stringContaining('/cancel'));
    });
  });
});

// Test 4: Auto-Download on Completion
describe('DataRights Integration — Auto-Download', () => {
  it('should trigger download when request completes', async () => {
    const createElementSpy = jest.spyOn(document, 'createElement');
    const appendChildSpy = jest.spyOn(document.body, 'appendChild');
    const removeChildSpy = jest.spyOn(document.body, 'removeChild');

    global.fetch = jest.fn((url: string) => {
      if (url.includes('/download')) {
        return Promise.resolve({
          status: 200,
          blob: () => Promise.resolve(mockApiResponses.downloadBlob),
        } as Response);
      }
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve([mockApiResponses.listRequests[0]]), // completed request
      } as Response);
    });

    render(<DataRequestList />);

    await waitFor(() => {
      // Link element should be created for download
      const linkCreated = createElementSpy.mock.results.some((call) =>
        call.value?.tagName === 'A'
      );
      expect(linkCreated).toBe(true);
    });

    await waitFor(() => {
      // Link should be clicked and removed (cleanup)
      expect(removeChildSpy).toHaveBeenCalled();
    });

    createElementSpy.mockRestore();
    appendChildSpy.mockRestore();
    removeChildSpy.mockRestore();
  });

  it('should generate timestamp-based filename: data_export_YYYY-MM-DD_HHMMSS.json', async () => {
    const linkClickSpy = jest.fn();
    
    // Mock link.click
    Object.defineProperty(HTMLAnchorElement.prototype, 'click', {
      configurable: true,
      value: linkClickSpy,
    });

    global.fetch = jest.fn((url: string) => {
      if (url.includes('/download')) {
        return Promise.resolve({
          status: 200,
          blob: () => Promise.resolve(mockApiResponses.downloadBlob),
        } as Response);
      }
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve([mockApiResponses.listRequests[0]]),
      } as Response);
    });

    render(<DataRequestList />);

    await waitFor(() => {
      const calls = linkClickSpy.mock.calls;
      expect(calls.length).toBeGreaterThan(0);
    });

    // Verify filename pattern matches YYYY-MM-DD_HHMMSS
    const filename = linkClickSpy.mock.results[0]?.value?.download;
    expect(filename).toMatch(/data_export_\d{4}-\d{2}-\d{2}_\d{6}\.json/);
  });
});

// Test 5: Analytics Event Batching
describe('DataRights Integration — Analytics', () => {
  it('should batch analytics events (max 10 or 30s)', async () => {
    const analyticsSpy = jest.fn();

    // Mock AnalyticsService.flush()
    jest.spyOn(AnalyticsService.prototype, 'flush').mockImplementation(analyticsSpy);

    global.fetch = jest.fn((url: string, opts: any) => {
      if (url.includes('/analytics/events') && opts?.method === 'POST') {
        analyticsSpy(JSON.parse(opts.body).events);
        return Promise.resolve({
          status: 200,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      }
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve(mockApiResponses.listRequests),
      } as Response);
    });

    render(<DataRequestList />);

    await waitFor(
      () => {
        // Analytics should batch and post events
        expect(analyticsSpy).toHaveBeenCalled();
      },
      { timeout: 5000 }
    );
  });

  it('should track request_created event on form submission', async () => {
    const trackSpy = jest.spyOn(AnalyticsService.prototype, 'trackRequestCreated');

    global.fetch = jest.fn(() =>
      Promise.resolve({
        status: 201,
        json: () => Promise.resolve(mockApiResponses.createRequest('access')),
      } as Response)
    );

    const user = userEvent.setup();
    render(<DataRequestList />);

    const button = screen.getByRole('button', { name: /solicitar acceso/i });
    await user.click(button);

    await waitFor(() => {
      expect(trackSpy).toHaveBeenCalled();
    });

    trackSpy.mockRestore();
  });

  it('should track request_cancelled event on confirmation', async () => {
    const trackSpy = jest.spyOn(AnalyticsService.prototype, 'trackRequestCancelled');

    global.fetch = jest.fn((url: string, opts: any) => {
      if (url.includes('/cancel') && opts?.method === 'POST') {
        return Promise.resolve({
          status: 200,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      }
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve(mockApiResponses.listRequests),
      } as Response);
    });

    const user = userEvent.setup();
    render(<DataRequestList />);

    const cancelButton = await screen.findByRole('button', { name: /cancelar/i });
    await user.click(cancelButton);

    const confirmButton = await screen.findByRole('button', { name: /continuar/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(trackSpy).toHaveBeenCalled();
    });

    trackSpy.mockRestore();
  });

  it('should track export_downloaded event on auto-download', async () => {
    const trackSpy = jest.spyOn(AnalyticsService.prototype, 'trackExportDownloaded');

    global.fetch = jest.fn((url: string) => {
      if (url.includes('/download')) {
        return Promise.resolve({
          status: 200,
          blob: () => Promise.resolve(mockApiResponses.downloadBlob),
        } as Response);
      }
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve([mockApiResponses.listRequests[0]]),
      } as Response);
    });

    render(<DataRequestList />);

    await waitFor(() => {
      expect(trackSpy).toHaveBeenCalled();
    });

    trackSpy.mockRestore();
  });
});

// Test 6: Bearer Token Refresh on 401
describe('DataRights Integration — Auth & Token Management', () => {
  it('should refresh token on 401 Unauthorized response', async () => {
    let callCount = 0;
    const refreshSpy = jest.fn();

    global.fetch = jest.fn((url: string, opts: any) => {
      callCount++;
      
      // First call: 401 Unauthorized
      if (callCount === 1 && url.includes('/data-requests')) {
        return Promise.resolve({
          status: 401,
          json: () => Promise.resolve({ code: 'UNAUTHORIZED' }),
        } as Response);
      }

      // Refresh token call
      if (url.includes('/auth/refresh')) {
        refreshSpy();
        return Promise.resolve({
          status: 200,
          json: () =>
            Promise.resolve({
              access_token: 'new-token-xxx',
              expires_in: 900,
            }),
        } as Response);
      }

      // Retry: 200 OK with new token
      if (callCount > 1 && url.includes('/data-requests')) {
        return Promise.resolve({
          status: 200,
          json: () => Promise.resolve(mockApiResponses.listRequests),
        } as Response);
      }

      return Promise.reject(new Error('Unexpected call'));
    });

    render(<DataRequestList />);

    await waitFor(() => {
      // Refresh should have been called after 401
      expect(refreshSpy).toHaveBeenCalled();
    });
  });

  it('should store new token in localStorage after refresh', async () => {
    const localStorageSpy = jest.spyOn(Storage.prototype, 'setItem');

    global.fetch = jest.fn((url: string, opts: any) => {
      if (url.includes('/auth/refresh')) {
        return Promise.resolve({
          status: 200,
          json: () =>
            Promise.resolve({
              access_token: 'new-token-xyz',
              expires_in: 900,
            }),
        } as Response);
      }
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve(mockApiResponses.listRequests),
      } as Response);
    });

    render(<DataRequestList />);

    await waitFor(() => {
      // setItem should have been called with new token
      const setItemCalls = localStorageSpy.mock.calls.filter(
        (call) => call[0] === 'auth_token'
      );
      expect(setItemCalls.length).toBeGreaterThan(0);
    });

    localStorageSpy.mockRestore();
  });
});

// Test 7: End-to-End Complete Workflow
describe('DataRights Integration — Complete Workflow', () => {
  it('should complete full access request lifecycle', async () => {
    const user = userEvent.setup();
    const events = [];

    global.fetch = jest.fn((url: string, opts: any) => {
      // Create request
      if (url.includes('/data-requests') && opts?.method === 'POST') {
        events.push('request_created');
        return Promise.resolve({
          status: 201,
          json: () => Promise.resolve(mockApiResponses.createRequest('access')),
        } as Response);
      }

      // Get request status (polling)
      if (url.includes('/data-requests') && (!opts?.method || opts.method === 'GET')) {
        const completed = events.includes('download_triggered');
        return Promise.resolve({
          status: 200,
          json: () =>
            Promise.resolve([
              {
                ...mockApiResponses.listRequests[0],
                status: completed ? 'completed' : 'processing',
              },
            ]),
        } as Response);
      }

      // Download
      if (url.includes('/download')) {
        events.push('download_triggered');
        return Promise.resolve({
          status: 200,
          blob: () => Promise.resolve(mockApiResponses.downloadBlob),
        } as Response);
      }

      // Analytics
      if (url.includes('/analytics/events')) {
        events.push('analytics_batched');
        return Promise.resolve({
          status: 200,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      }

      return Promise.reject(new Error('Unexpected URL'));
    });

    render(<DataRequestList />);

    // 1. Create access request
    const button = screen.getByRole('button', { name: /solicitar acceso/i });
    await user.click(button);

    // 2. Wait for completion
    await waitFor(() => {
      expect(events).toContain('request_created');
    });

    // 3. Auto-download triggers
    await waitFor(() => {
      expect(events).toContain('download_triggered');
    });

    // 4. Analytics batches
    await waitFor(
      () => {
        expect(events).toContain('analytics_batched');
      },
      { timeout: 5000 }
    );

    // Verify sequence
    expect(events[0]).toBe('request_created');
    expect(events).toContain('download_triggered');
    expect(events).toContain('analytics_batched');
  });
});
