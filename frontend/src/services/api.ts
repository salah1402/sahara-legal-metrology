/**
 * Core API Client & Configuration for SAHARA
 * Legal Metrology Inspection System
 *
 * Provides:
 * - Centralized API configuration
 * - Production backend support through Vite environment variables
 * - Local development support
 * - Unified fetch handling
 * - Timeout handling
 * - Authentication header support
 * - Consistent API errors
 */

export interface ApiConfig {
  baseUrl: string;
  timeoutMs: number;
  useDemoFixtures: boolean;
}

/**
 * Resolve the backend API base URL.
 *
 * VITE_API_URL should contain the backend root, for example:
 *
 * https://sahara-legal-metrology-ze1m.onrender.com
 *
 * The API routes themselves contain /api/...
 */
const resolveDefaultApiBase = (): string => {
  const envBaseUrl =
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL;

  if (envBaseUrl) {
    return String(envBaseUrl).replace(/\/+$/, "");
  }

  /**
   * Local development fallback.
   *
   * This is only used when no Vite API environment variable
   * has been configured.
   */
  if (import.meta.env.DEV) {
    return "http://127.0.0.1:8000";
  }

  /**
   * Production fallback.
   *
   * Normally VITE_API_URL should always be configured on Vercel.
   * This fallback prevents the application from silently pointing
   * to localhost in production.
   */
  return "https://sahara-legal-metrology-ze1m.onrender.com";
};

const DEFAULT_CONFIG: ApiConfig = {
  baseUrl: resolveDefaultApiBase(),
  timeoutMs: 45000,
  useDemoFixtures: false,
};

/**
 * Active runtime configuration.
 */
let activeConfig: ApiConfig = {
  ...DEFAULT_CONFIG,
};

/**
 * Return the current API configuration.
 */
export function getApiConfig(): ApiConfig {
  return {
    ...activeConfig,
  };
}

/**
 * Update API configuration.
 *
 * LocalStorage persistence is intentionally restricted to development.
 * This prevents an old localhost configuration from breaking the
 * production deployment.
 */
export function setApiConfig(updates: Partial<ApiConfig>): void {
  activeConfig = {
    ...activeConfig,
    ...updates,
  };

  if (import.meta.env.DEV) {
    try {
      localStorage.setItem(
        "sahara_api_config",
        JSON.stringify(activeConfig)
      );
    } catch {
      // Ignore localStorage errors.
    }
  }
}

/**
 * Restore locally saved API configuration during development only.
 *
 * IMPORTANT:
 * Production must always use the Vercel environment configuration.
 */
if (import.meta.env.DEV) {
  try {
    const saved = localStorage.getItem("sahara_api_config");

    if (saved) {
      const parsed = JSON.parse(saved);

      if (parsed && typeof parsed === "object") {
        activeConfig = {
          ...DEFAULT_CONFIG,
          ...parsed,
        };
      }
    }
  } catch {
    // Ignore invalid localStorage data.
  }
}

/**
 * Standardized API error.
 */
export class ApiError extends Error {
  status?: number;
  code?: string;
  details?: unknown;

  constructor(
    message: string,
    status?: number,
    code?: string,
    details?: unknown
  ) {
    super(message);

    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/**
 * Build a complete API URL.
 *
 * Examples:
 *
 * request("/api/ocr")
 * =>
 * https://sahara-legal-metrology-ze1m.onrender.com/api/ocr
 *
 * request("api/inspections")
 * =>
 * https://sahara-legal-metrology-ze1m.onrender.com/api/inspections
 */
function buildApiUrl(endpoint: string): string {
  const cleanBase = activeConfig.baseUrl.replace(/\/+$/, "");

  const cleanEndpoint = endpoint.startsWith("/")
    ? endpoint
    : `/${endpoint}`;

  return `${cleanBase}${cleanEndpoint}`;
}

/**
 * Standard HTTP request handler.
 */
export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = buildApiUrl(endpoint);

  const headers = new Headers(options.headers || {});

  /**
   * Do not manually set Content-Type for FormData.
   * The browser must generate the multipart boundary itself.
   */
  if (
    !headers.has("Content-Type") &&
    !(options.body instanceof FormData)
  ) {
    headers.set("Content-Type", "application/json");
  }

  /**
   * Add authentication token if available.
   */
  try {
    const token = localStorage.getItem("sahara_auth_token");

    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  } catch {
    // Ignore localStorage errors.
  }

  const controller = new AbortController();

  const timeoutId = window.setTimeout(() => {
    controller.abort();
  }, activeConfig.timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    window.clearTimeout(timeoutId);

    /**
     * Handle HTTP errors.
     */
    if (!response.ok) {
      let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
      let errorData: unknown = null;

      try {
        errorData = await response.json();

        if (
          errorData &&
          typeof errorData === "object"
        ) {
          const data = errorData as {
            message?: string;
            detail?: string;
          };

          if (data.message || data.detail) {
            errorMessage =
              data.message ||
              data.detail ||
              errorMessage;
          }
        }
      } catch {
        // Response was not JSON.
      }

      throw new ApiError(
        errorMessage,
        response.status,
        "HTTP_ERROR",
        errorData
      );
    }

    /**
     * No Content.
     */
    if (response.status === 204) {
      return {} as T;
    }

    /**
     * Parse JSON response.
     */
    return (await response.json()) as T;
  } catch (error: unknown) {
    window.clearTimeout(timeoutId);

    /**
     * Request timeout.
     */
    if (
      error instanceof DOMException &&
      error.name === "AbortError"
    ) {
      throw new ApiError(
        "Request timed out. The inspection backend took too long to respond.",
        408,
        "TIMEOUT"
      );
    }

    /**
     * Preserve our own API errors.
     */
    if (error instanceof ApiError) {
      throw error;
    }

    /**
     * Network-level failure.
     */
    const message =
      error instanceof Error
        ? error.message
        : "Unable to connect to the SAHARA inspection backend.";

    throw new ApiError(
      message,
      0,
      "NETWORK_ERROR"
    );
  }
}