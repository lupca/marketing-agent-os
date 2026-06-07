// src/lib/api.ts
// Centralized API client for The Autopilot Cockpit

import type {
  PaginatedRuns,
  PipelineRun,
  DagVisualization,
  QuarantinedTask,
  PaginatedQuarantinedTasks,
  KillSwitchStatus,
  AgencyState,
  User,
  AuthResponse,
  RegisterPayload,
  LoginPayload,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

// ─── Logout Callback Registry ──────────────────────────────────────────────────

let logoutHandler: (() => void) | null = null;

export function registerLogoutHandler(callback: () => void) {
  logoutHandler = callback;
}

// ─── Generic Fetch Helper ─────────────────────────────────────────────────────

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const headers: Record<string, string> = {};

  const isFormData = typeof FormData !== 'undefined' && options?.body instanceof FormData;
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  if (options?.headers) {
    Object.assign(headers, options.headers);
  }

  // Automatically append stored token if execution occurs in browser context
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    if (logoutHandler) {
      logoutHandler();
    }
  }

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API Error ${res.status}: ${err}`);
  }
  return res.json() as Promise<T>;
}


export const cockpitApi = {
  // ─── Pipeline Runs ────────────────────────────────────────────────────────

  getRuns: (params?: { page?: number; page_size?: number; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set('page', String(params.page));
    if (params?.page_size) qs.set('page_size', String(params.page_size));
    if (params?.status) qs.set('status', params.status);
    return apiFetch<PaginatedRuns>(`/api/cockpit/runs?${qs.toString()}`);
  },

  getRun: (runId: string) =>
    apiFetch<PipelineRun>(`/api/cockpit/runs/${runId}`),

  getDag: (runId: string) =>
    apiFetch<DagVisualization>(`/api/cockpit/runs/${runId}/dag`),

  // ─── Quarantine ───────────────────────────────────────────────────────────

  getQuarantinedTasks: () =>
    apiFetch<PaginatedQuarantinedTasks>('/api/cockpit/quarantine'),

  getQuarantinedTask: (taskId: string) =>
    apiFetch<QuarantinedTask>(`/api/cockpit/quarantine/${taskId}`),

  updateQuarantineState: (taskId: string, newState: AgencyState) =>
    apiFetch<QuarantinedTask>(`/api/cockpit/quarantine/${taskId}/state`, {
      method: 'PUT',
      body: JSON.stringify({ state: newState }),
    }),

  forceResumeTask: (taskId: string) =>
    apiFetch<{ status: string; run_id: string }>(`/api/cockpit/quarantine/${taskId}/resume`, {
      method: 'POST',
    }),

  discardTask: (taskId: string) =>
    apiFetch<{ status: string }>(`/api/cockpit/quarantine/${taskId}/discard`, {
      method: 'POST',
    }),

  // ─── Kill Switch ──────────────────────────────────────────────────────────

  getKillSwitch: () =>
    apiFetch<KillSwitchStatus>('/api/cockpit/kill-switch'),

  activateKillSwitch: (payload: { reason: string; activated_by?: string }) =>
    apiFetch<KillSwitchStatus>('/api/cockpit/kill-switch/activate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  deactivateKillSwitch: (payload?: { deactivated_by?: string }) =>
    apiFetch<KillSwitchStatus>('/api/cockpit/kill-switch/deactivate', {
      method: 'POST',
      body: JSON.stringify(payload ?? {}),
    }),
};

export const authApi = {
  register: (payload: RegisterPayload) =>
    apiFetch<AuthResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  login: (payload: LoginPayload) =>
    apiFetch<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getMe: () =>
    apiFetch<User>('/api/auth/me'),
};

