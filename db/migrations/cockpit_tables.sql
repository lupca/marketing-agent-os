-- Autopilot Cockpit Tables Migration
-- Pipeline Observability for Marketing Agent OS

-- 1. Pipeline Runs: tracks each autonomous graph execution
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES marketing_campaigns(id) ON DELETE SET NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'quarantined')),
    initial_state JSONB DEFAULT '{}',
    final_state JSONB DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

-- 2. Pipeline Node Executions: per-node I/O capture
CREATE TABLE IF NOT EXISTS pipeline_node_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    node_name VARCHAR(100) NOT NULL,
    node_order INTEGER DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    input_state JSONB DEFAULT '{}',
    output_state JSONB DEFAULT '{}',
    duration_ms INTEGER DEFAULT 0,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- 3. Quarantined Tasks: tasks isolated due to errors/circuit breaker
CREATE TABLE IF NOT EXISTS quarantined_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES pipeline_runs(id) ON DELETE SET NULL,
    node_name VARCHAR(100) NOT NULL,
    frozen_state JSONB NOT NULL DEFAULT '{}',
    quarantine_reason TEXT NOT NULL,
    resolution_status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (resolution_status IN ('pending', 'resumed', 'discarded')),
    resolved_by VARCHAR(255),
    original_state JSONB DEFAULT '{}',
    edited_state JSONB DEFAULT '{}',
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. System Kill Switch: global external API halt mechanism
CREATE TABLE IF NOT EXISTS system_kill_switch (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    activated_by VARCHAR(255),
    activated_at TIMESTAMPTZ,
    deactivated_at TIMESTAMPTZ,
    reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default kill switch record (inactive)
INSERT INTO system_kill_switch (workspace_id, is_active, reason)
SELECT id, FALSE, 'Initial state - all systems nominal'
FROM workspaces
LIMIT 1
ON CONFLICT DO NOTHING;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_workspace ON pipeline_runs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_node_executions_run ON pipeline_node_executions(run_id);
CREATE INDEX IF NOT EXISTS idx_quarantined_tasks_status ON quarantined_tasks(resolution_status);
CREATE INDEX IF NOT EXISTS idx_kill_switch_workspace ON system_kill_switch(workspace_id);
