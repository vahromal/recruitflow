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
