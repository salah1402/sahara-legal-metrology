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
  // If running in browser, dynamically check hostname
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    // Localhost development
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      const devUrl =
        import.meta.env.VITE_DEV_API_URL ||
        (import.meta.env.VITE_API_URL && (import.meta.env.VITE_API_URL.includes("localhost") || import.meta.env.VITE_API_URL.includes("127.0.0.1")) ? import.meta.env.VITE_API_URL : null);
      if (devUrl) {
        return String(devUrl).replace(/\/+$/, "");
      }
      return "http://127.0.0.1:8000";
    }

    // Production host (e.g. saharalegalmetrology.vercel.app or any external domain)
    // NEVER point to localhost under any circumstances
    const envBaseUrl =
      import.meta.env.VITE_API_BASE_URL ||
      import.meta.env.VITE_API_URL;

    if (envBaseUrl && !envBaseUrl.includes("localhost") && !envBaseUrl.includes("127.0.0.1")) {
      return String(envBaseUrl).replace(/\/+$/, "");
    }

    return "https://sahara-legal-metrology-ze1m.onrender.com";
  }

  // SSR or build-time fallback
  if (import.meta.env.DEV) {
    return "http://127.0.0.1:8000";
  }

  return "https://sahara-legal-metrology-ze1m.onrender.com";
};

const DEFAULT_CONFIG: ApiConfig = {
  baseUrl: resolveDefaultApiBase(),
  timeoutMs: 180000,
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

/**
 * Probes the backend health endpoint before starting an inspection.
 * If the cloud backend (Render) is sleeping, waking from cold start takes ~25-45 seconds.
 * 
 * This function:
 * 1. Probes the backend /health endpoint.
 * 2. If healthy, resolves immediately (0ms delay for awake backends).
 * 3. If unreachable or waking up (502/503/timeout), sets status to "Waking inspection service… Please wait."
 *    and retries every 3 seconds for up to maxWaitMs (90s max).
 * 4. As soon as the health check returns 200 OK, resolves so the inspection proceeds automatically
 *    without the user having to press "Start Inspection" again.
 * 5. If the backend fails to respond after 90 seconds, throws a descriptive ApiError.
 */
export async function ensureBackendAwake(
  onStatusUpdate?: (message: string) => void,
  maxWaitMs: number = 90000
): Promise<void> {
  const config = getApiConfig();
  const baseUrl = config.baseUrl.replace(/\/+$/, "");
  const healthUrl = `${baseUrl}/health`;

  const probeHealth = async (timeoutMs: number): Promise<boolean> => {
    try {
      const controller = new AbortController();
      const timer = window.setTimeout(() => controller.abort(), timeoutMs);
      const res = await fetch(healthUrl, {
        method: "GET",
        mode: "cors",
        signal: controller.signal,
      });
      window.clearTimeout(timer);
      return res.ok;
    } catch {
      // Fallback: probe root "/" endpoint in case /health is temporarily unavailable
      try {
        const controller = new AbortController();
        const timer = window.setTimeout(() => controller.abort(), Math.min(timeoutMs, 4000));
        const resRoot = await fetch(`${baseUrl}/`, {
          method: "GET",
          mode: "cors",
          signal: controller.signal,
        });
        window.clearTimeout(timer);
        return resRoot.ok;
      } catch {
        return false;
      }
    }
  };

  // 1. Initial quick probe (4000ms timeout)
  const isHealthyInitially = await probeHealth(4000);
  if (isHealthyInitially) {
    return;
  }

  // 2. Cold start detected. Start retry wait loop (up to maxWaitMs, ~90 seconds)
  const startTime = Date.now();
  onStatusUpdate?.("Waking inspection service… Please wait.");

  let attempt = 0;
  while (Date.now() - startTime < maxWaitMs) {
    attempt++;
    await new Promise((resolve) => setTimeout(resolve, 3000));

    onStatusUpdate?.("Waking inspection service… Please wait.");

    const isHealthy = await probeHealth(6000);
    if (isHealthy) {
      const elapsed = Math.round((Date.now() - startTime) / 1000);
      console.log(`Backend is online after ${elapsed}s (attempt ${attempt}). Resuming inspection...`);
      return;
    }
  }

  // 3. Genuine failure after 90 seconds
  const isLocal =
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1");

  const errorMsg = isLocal
    ? "Unable to connect to the local development backend. Make sure your local FastAPI service is running on http://127.0.0.1:8000."
    : `Unable to connect to the SAHARA inspection backend (${baseUrl}) after waiting 90 seconds. The service may be experiencing downtime; please wait a moment and try again.`;

  throw new ApiError(errorMsg, 0, "BACKEND_UNAVAILABLE");
}