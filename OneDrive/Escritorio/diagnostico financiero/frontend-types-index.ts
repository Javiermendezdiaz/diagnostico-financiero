// frontend/types/index.ts
// Reutiliza tipos del backend para type safety consistente

export type RequestStatus = 'pending' | 'processing' | 'completed' | 'cancelled' | 'failed';
export type RequesterType = 'individual' | 'proxy' | 'legal_representative';

export interface DataRequest {
  requestId: string;
  status: RequestStatus;
  requesterType: RequesterType;
  requesterName: string;
  requesterEmail: string;
  dataSubjectName?: string;
  dataCategories: string[];
  requestDate: number;
  estimatedCompletionDate: number;
  actualCompletionDate?: number;
  downloadUrl?: string;
  downloadExpiresAt?: number;
  cancellationReason?: string;
  cancellationDate?: number;
}

export interface CreateRequestPayload {
  requesterType: RequesterType;
  requesterName: string;
  requesterEmail: string;
  dataSubjectName?: string;
  dataCategories: string[];
}

export interface ListRequestsResponse {
  requests: DataRequest[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface CancelRequestPayload {
  cancellationReason: string;
}

export interface CancelRequestResponse {
  success: boolean;
  updatedRequest: DataRequest;
}

export interface RefreshTokenResponse {
  accessToken: string;
  expiresIn: number;
}

export interface AnalyticsSnapshot {
  requests: {
    count: number;
    byStatus: { [key in RequestStatus]: number };
    avgProcessingTime: number;
    completionRate: number;
  };
  performance: {
    pageLoad: { p50: number; p95: number; p99: number };
    requests: { p50: number; p95: number; p99: number };
    downloads: { successRate: number; avgSize: number };
    errors: { rate: number; topErrors: string[] };
    tokenRefresh: { uptime: number; p95: number };
  };
  sla: {
    complianceScore: number;
    uptime: number;
    violationCount: number;
  };
}

export interface ErrorResponse {
  error: string;
  statusCode: number;
  timestamp: number;
  requestId?: string;
}
