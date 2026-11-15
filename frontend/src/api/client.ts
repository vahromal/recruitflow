// Minimal typed API client with JWT support and unified error handling.
import { apiUrl, fetchWithRetry } from './base';

export class ApiError extends Error {
  code: string;
  status: number;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const TOKEN_KEY = 'rf_token';

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

interface RequestOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
  raw?: boolean; // return Response as-is (CSV, file download)
}

export async function api<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (opts.formData) {
    body = opts.formData;
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }

  const method = opts.method ?? 'GET';
  // Retry only idempotent requests: a POST that actually succeeded must not be
  // repeated (it could create a duplicate record).
  const idempotent = method === 'GET' || method === 'HEAD';
  const res = idempotent
    ? await fetchWithRetry(apiUrl(path), { method, headers, body })
    : await fetch(apiUrl(path), { method, headers, body });

  if (opts.raw) {
    if (!res.ok) throw await toApiError(res);
    return res as unknown as T;
  }

  if (res.status === 204) return undefined as T;

  if (!res.ok) throw await toApiError(res);

  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

async function toApiError(res: Response): Promise<ApiError> {
  let code = 'http_error';
  let message = `HTTP ${res.status}`;
  let details: unknown;
  try {
    const data = await res.json();
    if (data?.error) {
      code = data.error.code ?? code;
      message = data.error.message ?? message;
      details = data.error.details;
    } else if (data?.detail) {
      message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    }
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(res.status, code, message, details);
}

/** Trigger browser download of a protected endpoint (CSV export). */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const res = await api<Response>(path, { raw: true });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
