/**
 * Core API Client & Configuration for SAHARA — Legal Metrology Inspection System
 * Provides unified fetch abstraction, error classification, and production-ready backend connection handling.
 */

export interface ApiConfig {
  baseUrl: string;
  timeoutMs: number;
  useDemoFixtures: boolean;
}

// Configurable production backend URL via VITE_API_BASE_URL or VITE_API_URL
const resolveDefaultApiBase = (): string => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // In production builds, default to relative /api if served on same host, or localhost in dev
  return import.meta.env.PROD ? '/api' : 'http://127.0.0.1:8000/api';
};

const DEFAULT_CONFIG: ApiConfig = {
  baseUrl: resolveDefaultApiBase(),
  timeoutMs: 45000,
  useDemoFixtures: false, // Default to live PaddleOCR + Nemotron backend
};

let activeConfig: ApiConfig = { ...DEFAULT_CONFIG };

export function getApiConfig(): ApiConfig {
  return { ...activeConfig };
}

export function setApiConfig(updates: Partial<ApiConfig>) {
  activeConfig = { ...activeConfig, ...updates };
  try {
    localStorage.setItem('sahara_api_config', JSON.stringify(activeConfig));
  } catch (e) {
    // ignore localstorage errors
  }
}

// Initialize from localStorage if exists
try {
  const saved = localStorage.getItem('sahara_api_config');
  if (saved) {
    activeConfig = { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
  }
} catch (e) {
  // ignore
}

export class ApiError extends Error {
  status?: number;
  code?: string;
  details?: unknown;

  constructor(message: string, status?: number, code?: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/**
 * Standard HTTP Request handler
 */
export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const cleanBase = activeConfig.baseUrl.replace(/\/+$/, '');
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${cleanBase}${cleanEndpoint}`;
  
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Inject authorization header if token exists
  const token = localStorage.getItem('sahara_auth_token');
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), activeConfig.timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
      let errorData = null;
      try {
        errorData = await response.json();
        if (errorData?.message || errorData?.detail) {
          errorMessage = errorData.message || errorData.detail;
        }
      } catch {
        // response is not json
      }
      throw new ApiError(errorMessage, response.status, 'HTTP_ERROR', errorData);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new ApiError('Request timed out. The inspection backend took too long to respond.', 408, 'TIMEOUT');
    }
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error.message || 'Unable to connect to the SAHARA inspection backend. Make sure the FastAPI service is running on http://127.0.0.1:8000.',
      0,
      'NETWORK_ERROR'
    );
  }
}
