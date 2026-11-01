// Shared API types (mirror of backend Pydantic schemas)

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'recruiter';
  is_active: boolean;
}

export interface Candidate {
  id: number;
  full_name: string;
  phone: string | null;
  email: string | null;
  city: string | null;
  position: string | null;
  company: string | null;
  expected_salary: number | null;
  source: string | null;
  profile_links: string[];
  telegram: string | null;
  whatsapp: string | null;
  notes: string | null;
  tags: string[];
  owner_id: number;
  resume_filename: string | null;
  created_at: string;
  updated_at: string;
}

export interface StageHistoryItem {
  id: number;
  from_stage: string | null;
  to_stage: string;
  comment: string | null;
  author_id: number | null;
  created_at: string;
}

export interface Card {
  id: number;
  candidate_id: number;
  vacancy_id: number;
  stage: string;
  reject_reason: string | null;
  created_at: string;
  updated_at: string;
  candidate?: { id: number; full_name: string; position: string | null; expected_salary: number | null; tags: string[] };
  history: StageHistoryItem[];
}

export type Stage =
  | 'new' | 'screening' | 'interview_recruiter' | 'interview_client'
  | 'test_task' | 'offer' | 'hired' | 'rejected';

export const STAGES: { value: Stage; label: string }[] = [
  { value: 'new', label: 'Новый' },
  { value: 'screening', label: 'Скрининг' },
  { value: 'interview_recruiter', label: 'Интервью с рекрутером' },
  { value: 'interview_client', label: 'Интервью с заказчиком' },
  { value: 'test_task', label: 'Тестовое задание' },
  { value: 'offer', label: 'Оффер' },
  { value: 'hired', label: 'Принят' },
  { value: 'rejected', label: 'Отказ' },
];

export interface Vacancy {
  id: number;
  title: string;
  client: string | null;
  description: string | null;
  requirements: string | null;
  salary_min: number | null;
  salary_max: number | null;
  status: 'open' | 'paused' | 'closed';
  owner_id: number;
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: number;
  candidate_id: number;
  type: 'comment' | 'task' | 'event';
  body: string;
  due_at: string | null;
  task_status: 'open' | 'done' | null;
  author_id: number | null;
  created_at: string;
}

export interface DashboardData {
  stages: { stage: string; count: number }[];
  open_vacancies: number;
  tasks_today: number;
  total_candidates: number;
  recruiter_stats: {
    user_id: number;
    full_name: string;
    candidates: number;
    hired: number;
    rejected: number;
    open_vacancies: number;
  }[];
}
