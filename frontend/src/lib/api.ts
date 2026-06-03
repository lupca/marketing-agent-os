// src/lib/api.ts
// Centralized API client for The Autopilot Cockpit

import type {
  ExecutionModeResponse,
  PaginatedRuns,
  PipelineRun,
  DagVisualization,
  QuarantinedTask,
  PaginatedQuarantinedTasks,
  KillSwitchStatus,
  AgencyState,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

// ─── Generic Fetch Helper ─────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API Error ${res.status}: ${err}`);
  }
  return res.json() as Promise<T>;
}

// ─── Execution Mode ───────────────────────────────────────────────────────────

export const cockpitApi = {
  getExecutionMode: () =>
    apiFetch<ExecutionModeResponse>('/api/cockpit/execution-mode'),

  setExecutionMode: (mode: 'shadow' | 'live') =>
    apiFetch<ExecutionModeResponse>('/api/cockpit/execution-mode', {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),

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
