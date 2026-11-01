// Typed wrappers around backend endpoints.
import { api, downloadFile } from './client';
import type {
  Activity, Card, Candidate, DashboardData, Page, User, Vacancy,
} from './types';

// --- auth (OAuth2 password flow: form-encoded) ---
export const authApi = {
  loginForm: async (username: string, password: string): Promise<string> => {
    const form = new URLSearchParams({ username, password });
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data?.error?.message ?? 'Неверный email или пароль');
    }
    const data = await res.json();
    return data.access_token as string;
  },
  me: () => api<User>('/auth/me'),
};

// --- users (admin) ---
export const usersApi = {
  list: () => api<User[]>('/users'),
  create: (payload: { email: string; full_name: string; password: string; role: string }) =>
    api<User>('/users', { method: 'POST', body: payload }),
  update: (id: number, payload: Partial<{ full_name: string; password: string; role: string; is_active: boolean }>) =>
    api<User>(`/users/${id}`, { method: 'PATCH', body: payload }),
  remove: (id: number) => api<void>(`/users/${id}`, { method: 'DELETE' }),
};

// --- candidates ---
export interface CandidateFilters {
  page?: number;
  page_size?: number;
  q?: string;
  city?: string;
  position?: string;
  source?: string;
  tag?: string;
}

export const candidatesApi = {
  list: (f: CandidateFilters = {}) => {
    const params = new URLSearchParams();
    Object.entries(f).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.set(k, String(v));
    });
    return api<Page<Candidate>>(`/candidates?${params}`);
  },
  get: (id: number) => api<Candidate & { stages: Card[]; activities: Activity[] }>(`/candidates/${id}`),
  create: (payload: Partial<Candidate>) => api<Candidate>('/candidates', { method: 'POST', body: payload }),
  update: (id: number, payload: Partial<Candidate>) => api<Candidate>(`/candidates/${id}`, { method: 'PATCH', body: payload }),
  remove: (id: number) => api<void>(`/candidates/${id}`, { method: 'DELETE' }),
  uploadResume: (id: number, file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return api<Candidate>(`/candidates/${id}/resume`, { method: 'POST', formData: fd });
  },
  exportCsv: (q?: string) =>
    downloadFile(`/candidates/export${q ? `?q=${encodeURIComponent(q)}` : ''}`, 'candidates.csv'),
  checkDuplicates: (email?: string, phone?: string) =>
    api<{ candidate_id: number; full_name: string; matched_by: string }[]>(
      `/candidates/duplicates?email=${encodeURIComponent(email ?? '')}&phone=${encodeURIComponent(phone ?? '')}`
    ),
};

// --- vacancies ---
export const vacanciesApi = {
  list: (params: { page?: number; page_size?: number; status?: string; q?: string } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && qs.set(k, String(v)));
    return api<Page<Vacancy>>(`/vacancies?${qs}`);
  },
  get: (id: number) => api<Vacancy>(`/vacancies/${id}`),
  create: (payload: Partial<Vacancy>) => api<Vacancy>('/vacancies', { method: 'POST', body: payload }),
  update: (id: number, payload: Partial<Vacancy>) => api<Vacancy>(`/vacancies/${id}`, { method: 'PATCH', body: payload }),
  remove: (id: number) => api<void>(`/vacancies/${id}`, { method: 'DELETE' }),
  board: (id: number) =>
    api<{ vacancy_id: number; stages: Record<string, Card[]> }>(`/vacancies/${id}/board`),
  addCard: (vacancyId: number, candidateId: number) =>
    api<Card>(`/vacancies/${vacancyId}/cards`, { method: 'POST', body: { candidate_id: candidateId, vacancy_id: vacancyId } }),
  moveCard: (cardId: number, stage: string, opts: { reject_reason?: string; comment?: string } = {}) =>
    api<Card>(`/cards/${cardId}/move`, { method: 'POST', body: { stage, ...opts } }),
};

// --- activities ---
export const activitiesApi = {
  list: (candidateId: number, type?: string) =>
    api<Activity[]>(`/candidates/${candidateId}/activities${type ? `?type=${type}` : ''}`),
  comment: (candidateId: number, body: string) =>
    api<Activity>(`/candidates/${candidateId}/comments`, { method: 'POST', body: { body } }),
  createTask: (candidateId: number, body: string, dueAt?: string) =>
    api<Activity>(`/candidates/${candidateId}/tasks`, { method: 'POST', body: { body, due_at: dueAt } }),
  updateTask: (taskId: number, payload: { task_status?: string; body?: string; due_at?: string }) =>
    api<Activity>(`/tasks/${taskId}`, { method: 'PATCH', body: payload }),
  today: () => api<Activity[]>('/tasks/today'),
  feed: () => api<Activity[]>('/feed'),
};

// --- dashboard ---
export const dashboardApi = {
  get: () => api<DashboardData>('/dashboard'),
};

// --- gdpr ---
export const gdprApi = {
  exportCandidate: (id: number) => downloadFile(`/gdpr/candidates/${id}/export`, `candidate_${id}_gdpr.json`),
  eraseCandidate: (id: number) => api<void>(`/gdpr/candidates/${id}`, { method: 'DELETE' }),
};
