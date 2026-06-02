# core/pipeline_models.py
"""
SQLAlchemy models for The Autopilot Cockpit observability layer.
Tracks pipeline run executions, node-level I/O, quarantined tasks, and kill switch state.
"""
import uuid
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from db.connection import Base


class PipelineRun(Base):
    """
    Records each invocation of the autonomous LangGraph pipeline.
    Captures the full initial/final state and execution mode (shadow vs live).

    Attributes:
        id:             Primary key UUID.
        workspace_id:   FK to workspaces table.
        campaign_id:    FK to marketing_campaigns table (nullable — may not always have a campaign).
        execution_mode: 'shadow' (dry-run, no external publishing) or 'live' (full publishing enabled).
        status:         Lifecycle state: running → completed | failed | quarantined.
        initial_state:  JSONB snapshot of the state passed into graph.ainvoke().
        final_state:    JSONB snapshot of the state returned from graph.ainvoke().
        error_message:  Captured exception string if the run failed.
        started_at:     Wall-clock timestamp when the run began.
        completed_at:   Wall-clock timestamp when the run finished (any terminal state).
        metadata_:      Arbitrary key-value pairs for extensibility (stored as "metadata" column).
    """
    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True)
    execution_mode = Column(String(20), nullable=False, default="shadow")  # 'shadow' | 'live'
    status = Column(String(30), nullable=False, default="running")  # 'running' | 'completed' | 'failed' | 'quarantined'
    initial_state = Column(JSONB, default=dict)
    final_state = Column(JSONB, default=dict)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)


class PipelineNodeExecution(Base):
    """
    Tracks the execution of each individual node within a pipeline run.
    Captures input/output state diff for debugging and Glass-box monitoring.

    Attributes:
        id:             Primary key UUID.
        run_id:         FK to pipeline_runs — parent run this node belongs to.
        node_name:      Name of the LangGraph node (e.g. 'scoring', 'publisher').
        node_order:     Numeric ordering for DAG visualization (1–6 for the 6-node pipeline).
        status:         Node lifecycle: pending → running → completed | failed | skipped.
        input_state:    JSONB snapshot of the AgencyState passed INTO this node.
        output_state:   JSONB snapshot of the dict returned BY this node.
        duration_ms:    Execution wall-clock duration in milliseconds.
        error_message:  Captured exception string if the node failed.
        retry_count:    Number of retry attempts before the final status.
        started_at:     Timestamp when node execution began.
        completed_at:   Timestamp when node execution ended.
    """
    __tablename__ = "pipeline_node_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)
    node_name = Column(String(100), nullable=False)
    node_order = Column(Integer, default=0)
    status = Column(String(30), nullable=False, default="pending")  # 'pending' | 'running' | 'completed' | 'failed'
    input_state = Column(JSONB, default=dict)
    output_state = Column(JSONB, default=dict)
    duration_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class QuarantinedTask(Base):
    """
    Holds pipeline tasks that have been isolated due to errors or circuit breaker triggers.
    Engineers can edit the frozen_state JSON and force-resume from the quarantined node.

    Attributes:
        id:                 Primary key UUID.
        run_id:             FK to pipeline_runs (nullable — run may be cleaned up independently).
        node_name:          The node at which execution was halted and quarantined.
        frozen_state:       JSONB copy of the AgencyState at the point of quarantine.
        quarantine_reason:  Human-readable explanation of why the task was quarantined.
        resolution_status:  'pending' | 'resumed' (manually restarted) | 'discarded' (dropped).
        resolved_by:        Username or system identifier of who resolved this task.
        original_state:     Immutable copy of the original frozen_state before any edits.
        edited_state:       JSONB representing the engineer's corrected state for resume.
        resolved_at:        Timestamp when a resolution action was taken.
        created_at:         Timestamp when the task was quarantined.
    """
    __tablename__ = "quarantined_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True)
    node_name = Column(String(100), nullable=False)
    frozen_state = Column(JSONB, nullable=False, default=dict)
    quarantine_reason = Column(Text, nullable=False)
    resolution_status = Column(String(30), nullable=False, default="pending")  # 'pending' | 'resumed' | 'discarded'
    resolved_by = Column(String(255), nullable=True)
    original_state = Column(JSONB, default=dict)
    edited_state = Column(JSONB, default=dict)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SystemKillSwitch(Base):
    """
    Global kill switch for halting all external API calls (Facebook Ads, social publishing).
    When is_active=True, publisher_node and Celery social tasks are blocked.
    The internal LangGraph pipeline continues running for analysis and insight generation.

    Design note:
        One row per workspace. The default record is seeded with is_active=False.
        Operators activate/deactivate via the /api/cockpit/kill-switch endpoints.

    Attributes:
        id:             Primary key UUID.
        workspace_id:   FK to workspaces (nullable for system-wide switches).
        is_active:      Master flag — True blocks all outbound API calls.
        activated_by:   Identity string (user email or 'system') who flipped the switch ON.
        activated_at:   Timestamp of the most recent activation event.
        deactivated_at: Timestamp of the most recent deactivation event.
        reason:         Operator note explaining why the switch was activated.
        metadata_:      Extensible JSONB for incident tracking metadata.
        created_at:     Row creation timestamp.
        updated_at:     Row last-update timestamp (auto-managed by SQLAlchemy onupdate).
    """
    __tablename__ = "system_kill_switch"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)
    activated_by = Column(String(255), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
