// src/lib/types.ts
// Shared TypeScript interfaces for The Autopilot Cockpit

export type RunStatus = 'running' | 'completed' | 'failed' | 'quarantined';
export type NodeStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export type ResolutionStatus = 'pending' | 'resumed' | 'discarded';

// ─── Pipeline Run ───────────────────────────────────────────────────────────

export interface PipelineRun {
  id: string;
  workspace_id: string | null;
  campaign_id: string | null;
  status: RunStatus;
  initial_state: AgencyState;
  final_state: AgencyState | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  metadata: Record<string, unknown>;
  nodes?: PipelineNodeExecution[];
}

// ─── Node Execution ──────────────────────────────────────────────────────────

export interface PipelineNodeExecution {
  id: string;
  run_id: string;
  node_name: NodeName;
  node_order: number;
  status: NodeStatus;
  input_state: AgencyState;
  output_state: AgencyState | null;
  duration_ms: number;
  error_message: string | null;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
}

// ─── Quarantined Task ────────────────────────────────────────────────────────

export interface QuarantinedTask {
  id: string;
  run_id: string | null;
  node_name: NodeName;
  frozen_state: AgencyState;
  quarantine_reason: string;
  resolution_status: ResolutionStatus;
  resolved_by: string | null;
  original_state: AgencyState;
  edited_state: AgencyState | null;
  resolved_at: string | null;
  created_at: string;
}

// ─── Kill Switch ─────────────────────────────────────────────────────────────

export interface KillSwitchStatus {
  id: string;
  is_active: boolean;
  activated_by: string | null;
  activated_at: string | null;
  deactivated_at: string | null;
  reason: string | null;
}

// ─── LangGraph State ─────────────────────────────────────────────────────────

export interface AgencyState {
  workspace_id?: string;
  campaign_id?: string;
  product_id?: string;
  campaign_objective?: string;
  current_metrics?: Record<string, number>;
  current_beliefs?: Record<string, number>;
  sop_stage?: string;
  selected_actions?: Array<{ angle: string; belief?: number }>;
  generated_variants?: GeneratedVariant[];
  sandbox_feedbacks?: SandboxFeedback[];
  _run_id?: string;
  [key: string]: unknown;
}

export interface GeneratedVariant {
  variant_id: string;
  adapted_copy: string;
  angle_name: string;
  platform: string;
  tone_markers: string[];
}

export interface SandboxFeedback {
  angle: string;
  score: number;
  reason: string;
  stage?: string;
  error?: string;
}

// ─── DAG Visualization ───────────────────────────────────────────────────────

export type NodeName =
  | 'scoring'
  | 'selector'
  | 'creative_generation'
  | 'guardian_sandbox'
  | 'insight_generator'
  | 'publisher';

export interface DagNode {
  name: NodeName;
  label: string;
  order: number;
  status: NodeStatus;
  duration_ms: number;
  retry_count: number;
  has_error: boolean;
  error_message: string | null;
  execution_id: string | null;
}

export interface DagEdge {
  from: NodeName;
  to: NodeName;
  type: 'normal' | 'conditional' | 'retry';
  label?: string;
}

// ─── WebSocket Events ─────────────────────────────────────────────────────────

export type CockpitEventType =
  | 'run_start'
  | 'run_complete'
  | 'run_fail'
  | 'node_start'
  | 'node_complete'
  | 'node_fail'
  | 'quarantine'
  | 'kill_switch';

export interface CockpitWebSocketEvent {
  type: CockpitEventType;
  timestamp: string;
  data: Record<string, unknown>;
}

// ─── API Responses ────────────────────────────────────────────────────────────

export interface PaginatedRuns {
  runs: PipelineRun[];
  total: number;
  page: number;
  page_size: number;
}

export interface PaginatedQuarantinedTasks {
  tasks: QuarantinedTask[];
  total: number;
  page: number;
  page_size: number;
}

export interface DagVisualization {
  run_id: string;
  status: RunStatus;
  nodes: DagNode[];
  edges: DagEdge[];
}

// ─── Shadow Decision ──────────────────────────────────────────────────────────

export interface ShadowDecision {
  run_id: string;
  campaign_id: string | null;
  started_at: string;
  mab_beliefs: Record<string, number>;
  selected_angles: Array<{ angle: string; belief?: number }>;
  projected_variants: number;
  estimated_spend: string;
  status: RunStatus;
  variants?: GeneratedVariant[];
  sandbox_results?: SandboxFeedback[];
}

// ─── Authentication Models ───────────────────────────────────────────────────

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password?: string;
}

export interface LoginPayload {
  username?: string;
  email?: string;
  password?: string;
}

export interface Workspace {
  id: string;
  name: string;
}

export interface Campaign {
  id: string;
  name: string;
  workspace_id: string;
  campaign_type?: string;
}

