import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConsentManager } from './ConsentManager';
import * as useDataRightsModule from '@/hooks/useDataRights';

// Mock the hook
jest.mock('@/hooks/useDataRights');
const mockUseDataRights = jest.mocked(useDataRightsModule.useDataRights);

describe('ConsentManager', () => {
  const mockConsents = [
    {
      id: 'c1',
      consent_type: 'pdf_generation',
      granted_at: '2025-01-15T10:00:00Z',
      expires_at: '2026-01-15T10:00:00Z',
      is_withdrawn: false,
      withdrawn_at: null,
    },
    {
      id: 'c2',
      consent_type: 'email_communication',
      granted_at: '2025-02-01T14:30:00Z',
      expires_at: '2024-12-01T14:30:00Z', // Expired
      is_withdrawn: false,
      withdrawn_at: null,
    },
    {
      id: 'c3',
      consent_type: 'analytics',
      granted_at: '2024-11-01T09:00:00Z',
      expires_at: '2025-11-01T09:00:00Z',
      is_withdrawn: true,
      withdrawn_at: '2025-03-01T16:45:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders loading state initially', () => {
    mockUseDataRights.mockReturnValue({
      consents: [],
      loading: true,
      error: null,
      withdrawConsent: jest.fn(),
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);
    expect(screen.getByText('Cargando consentimientos...')).toBeInTheDocument();
  });

  test('renders error state', () => {
    const errorMessage = 'Fallo al conectar con el servidor';
    mockUseDataRights.mockReturnValue({
      consents: [],
      loading: false,
      error: errorMessage,
      withdrawConsent: jest.fn(),
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  test('renders empty state when no consents', () => {
    mockUseDataRights.mockReturnValue({
      consents: [],
      loading: false,
      error: null,
      withdrawConsent: jest.fn(),
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);
    expect(screen.getByText('No tienes consentimientos activos')).toBeInTheDocument();
  });

  test('renders consent table with correct data', () => {
    mockUseDataRights.mockReturnValue({
      consents: mockConsents,
      loading: false,
      error: null,
      withdrawConsent: jest.fn(),
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);

    // Check headers
    expect(screen.getByText('Tipo de consentimiento')).toBeInTheDocument();
    expect(screen.getByText('Otorgado')).toBeInTheDocument();
    expect(screen.getByText('Expira')).toBeInTheDocument();

    // Check consent rows (labels)
    expect(screen.getByText('Generación de PDFs')).toBeInTheDocument();
    expect(screen.getByText('Comunicación por email')).toBeInTheDocument();
    expect(screen.getByText('Analítica y mejora')).toBeInTheDocument();
  });

  test('shows correct badge statuses', () => {
    mockUseDataRights.mockReturnValue({
      consents: mockConsents,
      loading: false,
      error: null,
      withdrawConsent: jest.fn(),
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);

    // First consent: Active
    expect(screen.getByText('Activo')).toBeInTheDocument();

    // Second consent: Expired
    expect(screen.getByText('Expirado')).toBeInTheDocument();

    // Third consent: Retracted
    expect(screen.getByText('Retirado')).toBeInTheDocument();
  });

  test('opens withdrawal modal on withdraw button click', async () => {
    const withdrawMock = jest.fn();
    mockUseDataRights.mockReturnValue({
      consents: mockConsents,
      loading: false,
      error: null,
      withdrawConsent: withdrawMock,
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);

    // Click first "Revocar" button
    const withdrawButtons = screen.getAllByRole('button', { name: /Revocar/i });
    fireEvent.click(withdrawButtons[0]);

    // Check modal title
    await waitFor(() => {
      expect(screen.getByText('¿Revocar consentimiento?')).toBeInTheDocument();
    });
  });

  test('calls withdrawConsent on modal confirmation', async () => {
    const withdrawMock = jest.fn().mockResolvedValue(undefined);
    mockUseDataRights.mockReturnValue({
      consents: mockConsents,
      loading: false,
      error: null,
      withdrawConsent: withdrawMock,
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);

    // Open modal
    const withdrawButtons = screen.getAllByRole('button', { name: /Revocar/i });
    fireEvent.click(withdrawButtons[0]);

    // Click confirm button in modal
    await waitFor(() => {
      const confirmButton = screen.getAllByRole('button', { name: /Revocar/i })[1];
      fireEvent.click(confirmButton);
    });

    // Check that withdrawConsent was called
    await waitFor(() => {
      expect(withdrawMock).toHaveBeenCalledWith('c1');
    });
  });

  test('shows success message after successful withdrawal', async () => {
    const withdrawMock = jest.fn().mockResolvedValue(undefined);
    mockUseDataRights.mockReturnValue({
      consents: mockConsents,
      loading: false,
      error: null,
      withdrawConsent: withdrawMock,
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);

    // Open modal
    const withdrawButtons = screen.getAllByRole('button', { name: /Revocar/i });
    fireEvent.click(withdrawButtons[0]);

    // Confirm withdrawal
    await waitFor(() => {
      const confirmButton = screen.getAllByRole('button', { name: /Revocar/i })[1];
      fireEvent.click(confirmButton);
    });

    // Check success message
    await waitFor(() => {
      expect(screen.getByText('Consentimiento retirado correctamente')).toBeInTheDocument();
    });
  });

  test('disables withdraw button for expired consents', () => {
    mockUseDataRights.mockReturnValue({
      consents: mockConsents,
      loading: false,
      error: null,
      withdrawConsent: jest.fn(),
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);

    const actionCells = screen.getAllByText('—');
    // Two expiredconsents (one expired, one already retracted)
    expect(actionCells.length).toBeGreaterThan(0);
  });

  test('closes modal on escape key', async () => {
    mockUseDataRights.mockReturnValue({
      consents: mockConsents,
      loading: false,
      error: null,
      withdrawConsent: jest.fn(),
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);

    // Open modal
    const withdrawButtons = screen.getAllByRole('button', { name: /Revocar/i });
    fireEvent.click(withdrawButtons[0]);

    // Press escape
    await waitFor(() => {
      fireEvent.keyDown(window, { key: 'Escape' });
    });

    // Modal should be closed (no longer visible)
    await waitFor(() => {
      expect(screen.queryByText('¿Revocar consentimiento?')).not.toBeInTheDocument();
    });
  });

  test('renders compliance notice', () => {
    mockUseDataRights.mockReturnValue({
      consents: mockConsents,
      loading: false,
      error: null,
      withdrawConsent: jest.fn(),
      fetchConsents: jest.fn(),
      startPolling: jest.fn(),
    } as any);

    render(<ConsentManager />);

    expect(screen.getByText('Tus derechos')).toBeInTheDocument();
    expect(screen.getByText(/Art. 7\(3\) GDPR/)).toBeInTheDocument();
  });
});
