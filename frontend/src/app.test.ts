// Basic frontend tests: stage labels, API client error handling.
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { STAGES } from './api/types';
import { ApiError, api, tokenStore } from './api/client';

describe('STAGES constants', () => {
  it('contains all 8 pipeline stages in order', () => {
    expect(STAGES).toHaveLength(8);
    expect(STAGES.map((s) => s.value)).toEqual([
      'new', 'screening', 'interview_recruiter', 'interview_client',
      'test_task', 'offer', 'hired', 'rejected',
    ]);
  });

  it('has Russian labels for every stage', () => {
    for (const s of STAGES) {
      expect(s.label.length).toBeGreaterThan(0);
      expect(/[А-Яа-яЁё]/.test(s.label)).toBe(true);
    }
  });
});

describe('api client', () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends Authorization header when token is stored', async () => {
    tokenStore.set('test-token');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    await api('/auth/me');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/auth/me');
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer test-token');
  });

  it('parses unified error envelope into ApiError', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ error: { code: 'duplicate_candidate', message: 'Duplicate candidate exists' } }),
        { status: 409 }
      )
    );

    const err = (await api('/candidates', { method: 'POST', body: {} }).catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(409);
    expect(err.code).toBe('duplicate_candidate');
    expect(err.message).toBe('Duplicate candidate exists');
  });

  it('returns undefined on 204 responses', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }));
    await expect(api('/candidates/1', { method: 'DELETE' })).resolves.toBeUndefined();
  });
});
