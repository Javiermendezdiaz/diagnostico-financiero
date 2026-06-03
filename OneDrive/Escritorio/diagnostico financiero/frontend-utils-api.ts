// frontend/utils/api.ts
import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  DataRequest,
  CreateRequestPayload,
  ListRequestsResponse,
  CancelRequestPayload,
  CancelRequestResponse,
  RefreshTokenResponse,
  AnalyticsSnapshot,
  ErrorResponse,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3001';

class GDPRApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Interceptor para añadir token a cada request
    this.client.interceptors.request.use((config) => {
      if (this.accessToken) {
        config.headers.Authorization = `Bearer ${this.accessToken}`;
      }
      return config;
    });

    // Interceptor para manejar errores 401 y renovar token
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && this.refreshToken && originalRequest) {
          try {
            const response = await this.refreshAccessToken();
            this.accessToken = response.accessToken;

            // Reintentar request original con nuevo token
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${this.accessToken}`;
            }
            return this.client(originalRequest);
          } catch (refreshError) {
            // Si refresh falla, limpiar tokens y redirigir a login
            this.clearTokens();
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );

    // Cargar tokens del localStorage si existen
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('accessToken');
      this.refreshToken = localStorage.getItem('refreshToken');
    }
  }

  // Endpoint 1: Crear solicitud GDPR
  async createRequest(payload: CreateRequestPayload): Promise<DataRequest> {
    try {
      const response = await this.client.post<DataRequest>('/api/requests/create', payload);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Endpoint 2: Listar solicitudes con paginación y filtros
  async listRequests(
    page: number = 1,
    pageSize: number = 10,
    status?: string,
    requesterType?: string
  ): Promise<ListRequestsResponse> {
    try {
      const response = await this.client.get<ListRequestsResponse>('/api/requests/list', {
        params: {
          page,
          pageSize,
          ...(status && { status }),
          ...(requesterType && { requesterType }),
        },
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Endpoint 3: Obtener detalle de solicitud
  async getRequest(id: string): Promise<DataRequest> {
    try {
      const response = await this.client.get<DataRequest>(`/api/requests/${id}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Endpoint 4: Cancelar solicitud
  async cancelRequest(id: string, reason: string): Promise<CancelRequestResponse> {
    try {
      const response = await this.client.post<CancelRequestResponse>(
        `/api/requests/${id}/cancel`,
        { cancellationReason: reason }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Endpoint 5: Descargar datos compilados
  async downloadRequest(id: string): Promise<Blob> {
    try {
      const response = await this.client.get<Blob>(`/api/requests/${id}/download`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Endpoint 6: Renovar token de autenticación
  private async refreshAccessToken(): Promise<RefreshTokenResponse> {
    try {
      const response = await this.client.post<RefreshTokenResponse>('/api/auth/refresh', {
        refreshToken: this.refreshToken,
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Endpoint 7: Obtener dashboard de analytics
  async getAnalytics(): Promise<AnalyticsSnapshot> {
    try {
      const response = await this.client.get<AnalyticsSnapshot>('/api/analytics/dashboard');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: number }> {
    try {
      const response = await this.client.get<{ status: string; timestamp: number }>('/health');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Setear tokens de autenticación
  setTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    if (typeof window !== 'undefined') {
      localStorage.setItem('accessToken', accessToken);
      localStorage.setItem('refreshToken', refreshToken);
    }
  }

  // Limpiar tokens
  private clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
    }
  }

  // Manejo centralizado de errores
  private handleError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data as ErrorResponse | undefined;
      const message = errorData?.error || error.message;
      const statusCode = error.response?.status || 500;

      const customError = new Error(message);
      (customError as any).statusCode = statusCode;
      return customError;
    }

    return error instanceof Error ? error : new Error('Unknown error');
  }
}

// Singleton
export const apiClient = new GDPRApiClient();
