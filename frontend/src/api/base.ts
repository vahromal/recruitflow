// Base URL of the backend API.
//
// Empty string means "same origin": local dev (Vite proxy) and Docker (nginx proxy).
// For GitHub Pages the frontend lives on a different host, so the API address is
// injected at build time: VITE_API_BASE=https://<backend>.onrender.com
export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/+$/, '');

/** Build an absolute (or same-origin) URL for a backend route starting with /api. */
export function apiUrl(path: string): string {
  return `${API_BASE}/api${path}`;
}

/** Health-check URL (used to wake a sleeping free-tier backend). */
export function healthUrl(): string {
  return `${API_BASE}/health`;
}

/**
 * fetch with retries for transient network failures.
 *
 * The free Render backend sleeps after 15 minutes of inactivity and the first
 * request after that may be dropped while the service boots (~1 minute), which
 * surfaces in the browser as "NetworkError when attempting to fetch resource".
 */
export async function fetchWithRetry(
  input: RequestInfo | URL,
  init?: RequestInit,
  opts: { attempts?: number; onRetry?: (attempt: number) => void } = {},
): Promise<Response> {
  const attempts = opts.attempts ?? 7;
  const delays = [2000, 3000, 5000, 8000, 12000, 15000, 20000];
  let lastError: unknown;
  for (let i = 0; i < attempts; i += 1) {
    try {
      return await fetch(input, init);
    } catch (err) {
      lastError = err;
      if (i === attempts - 1) break;
      opts.onRetry?.(i + 1);
      await new Promise((resolve) => setTimeout(resolve, delays[Math.min(i, delays.length - 1)]));
    }
  }
  throw lastError;
}

