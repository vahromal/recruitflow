import '@testing-library/jest-dom/vitest';

// Node 26 exposes an experimental `localStorage` global that is unavailable
// without a CLI flag; jsdom may not override it. Provide a minimal fallback
// so tokenStore/localStorage usage in tests works everywhere.
try {
  if (!globalThis.localStorage || typeof globalThis.localStorage.getItem !== 'function') {
    throw new Error('missing');
  }
} catch {
  const store = new Map<string, string>();
  const fallback = {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => void store.set(k, String(v)),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    get length() {
      return store.size;
    },
  };
  Object.defineProperty(globalThis, 'localStorage', {
    value: fallback,
    configurable: true,
    writable: true,
  });
}
