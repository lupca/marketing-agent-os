# api/cockpit_routes.py
"""
Autopilot Cockpit API Routes — FastAPI router for the Cockpit monitoring dashboard.

Provides:
    - Pipeline run listing and detail view
    - DAG node-status visualization endpoint
    - Quarantined task management (list, view, edit state, resume, discard)
    - Kill switch activation / deactivation

All endpoints are prefixed with /api/cockpit and tagged "Cockpit" in the OpenAPI docs.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.dependencies import get_db
from core.pipeline_models import (
    PipelineRun,
    PipelineNodeExecution,
    QuarantinedTask,
    SystemKillSwitch,
)
from core import pipeline_tracker

logger = logging.getLogger("cockpit_routes")

cockpit_router = APIRouter(prefix="/api/cockpit", tags=["Cockpit"])


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────────────────────




class NodeExecutionSchema(BaseModel):
    """Serialized representation of a single pipeline node execution record."""
    id: str
    node_name: str
    node_order: int
    status: str
    duration_ms: int
    retry_count: int
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    input_state: Optional[Dict[str, Any]] = None
    output_state: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class PipelineRunSummary(BaseModel):
    """Lightweight run summary for list endpoints."""
    id: str
    status: str
    campaign_id: Optional[str]
    workspace_id: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class PipelineRunDetail(BaseModel):
    """Full run detail including all node executions."""
    id: str
    status: str
    campaign_id: Optional[str]
    workspace_id: Optional[str]
    initial_state: Optional[Dict[str, Any]]
    final_state: Optional[Dict[str, Any]]
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    nodes: List[NodeExecutionSchema] = []

    class Config:
        from_attributes = True


class DAGNodeStatus(BaseModel):
    """Status of a single DAG node for visualization."""
    node_name: str
    node_order: int
    status: str  # 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'not_started'
    duration_ms: int
    error_message: Optional[str]


class DAGResponse(BaseModel):
    """Full DAG state for a pipeline run — consumed by the frontend graph renderer."""
    run_id: str
    run_status: str
    nodes: List[DAGNodeStatus]


class QuarantinedTaskSummary(BaseModel):
    """Lightweight quarantined task for list endpoints."""
    id: str
    run_id: Optional[str]
    node_name: str
    quarantine_reason: str
    resolution_status: str
    created_at: Optional[str]

    class Config:
        from_attributes = True


class QuarantinedTaskDetail(BaseModel):
    """Full quarantined task detail including frozen and edited states."""
    id: str
    run_id: Optional[str]
    node_name: str
    frozen_state: Dict[str, Any]
    original_state: Dict[str, Any]
    edited_state: Dict[str, Any]
    quarantine_reason: str
    resolution_status: str
    resolved_by: Optional[str]
    resolved_at: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class EditFrozenStateRequest(BaseModel):
    """Request body for patching the editable state of a quarantined task."""
    edited_state: Dict[str, Any] = Field(
        ..., description="The corrected AgencyState JSON that will be used on resume."
    )


class ResumeQuarantineRequest(BaseModel):
    """Request body for force-resuming a quarantined task."""
    resumed_by: str = Field(
        ..., description="Username or identifier of the operator resuming the task."
    )
    workspace_id: str = Field(
        ..., description="Workspace UUID string for context."
    )
    campaign_id: Optional[str] = Field(
        None, description="Campaign UUID string (used to look up product_id)."
    )
    product_id: Optional[str] = Field(
        None, description="Product UUID string required to re-invoke the pipeline."
    )


class DiscardQuarantineRequest(BaseModel):
    """Request body for discarding a quarantined task without resuming."""
    discarded_by: str = Field(
        ..., description="Username or identifier of the operator discarding the task."
    )


class KillSwitchStatus(BaseModel):
    """Current kill switch state."""
    is_active: bool
    activated_by: Optional[str]
    activated_at: Optional[str]
    deactivated_at: Optional[str]
    reason: Optional[str]
    workspace_id: Optional[str]


class ActivateKillSwitchRequest(BaseModel):
    """Request body for activating the kill switch."""
    workspace_id: str = Field(..., description="Target workspace UUID string.")
    activated_by: str = Field(..., description="Operator name or email.")
    reason: str = Field(..., description="Audit-trail reason for activation.")


class DeactivateKillSwitchRequest(BaseModel):
    """Request body for deactivating the kill switch."""
    workspace_id: str = Field(..., description="Target workspace UUID string.")
    deactivated_by: str = Field(..., description="Operator name or email.")


# ─────────────────────────────────────────────────────────────────────────────
# Internal Serialisation Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _dt_str(dt: Optional[datetime]) -> Optional[str]:
    """Convert a datetime to ISO-8601 string, handling None gracefully."""
    if dt is None:
        return None
    return dt.isoformat()


def _run_to_summary(run: PipelineRun) -> PipelineRunSummary:
    return PipelineRunSummary(
        id=str(run.id),
        status=run.status,
        campaign_id=str(run.campaign_id) if run.campaign_id else None,
        workspace_id=str(run.workspace_id) if run.workspace_id else None,
        started_at=_dt_str(run.started_at),
        completed_at=_dt_str(run.completed_at),
        error_message=run.error_message,
    )


def _node_to_schema(n: PipelineNodeExecution) -> NodeExecutionSchema:
    return NodeExecutionSchema(
        id=str(n.id),
        node_name=n.node_name,
        node_order=n.node_order or 0,
        status=n.status,
        duration_ms=n.duration_ms or 0,
        retry_count=n.retry_count or 0,
        error_message=n.error_message,
        started_at=_dt_str(n.started_at),
        completed_at=_dt_str(n.completed_at),
        input_state=n.input_state or {},
        output_state=n.output_state or {},
    )


def _qt_to_summary(qt: QuarantinedTask) -> QuarantinedTaskSummary:
    return QuarantinedTaskSummary(
        id=str(qt.id),
        run_id=str(qt.run_id) if qt.run_id else None,
        node_name=qt.node_name,
        quarantine_reason=qt.quarantine_reason,
        resolution_status=qt.resolution_status,
        created_at=_dt_str(qt.created_at),
    )


def _qt_to_detail(qt: QuarantinedTask) -> QuarantinedTaskDetail:
    return QuarantinedTaskDetail(
        id=str(qt.id),
        run_id=str(qt.run_id) if qt.run_id else None,
        node_name=qt.node_name,
        frozen_state=qt.frozen_state or {},
        original_state=qt.original_state or {},
        edited_state=qt.edited_state or {},
        quarantine_reason=qt.quarantine_reason,
        resolution_status=qt.resolution_status,
        resolved_by=qt.resolved_by,
        resolved_at=_dt_str(qt.resolved_at),
        created_at=_dt_str(qt.created_at),
    )





# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Run Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@cockpit_router.get(
    "/runs",
    response_model=Dict[str, Any],
    summary="List pipeline runs (paginated)",
    description=(
        "Returns a paginated list of pipeline runs ordered by start time descending. "
        "Use 'status' query param to filter by run status."
    ),
)
async def list_runs(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Runs per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    workspace_id: Optional[str] = Query(None, description="Filter by workspace UUID"),
) -> Dict[str, Any]:
    query = db.query(PipelineRun).order_by(PipelineRun.started_at.desc())
    if status:
        query = query.filter(PipelineRun.status == status)
    if workspace_id:
        try:
            query = query.filter(
                PipelineRun.workspace_id == uuid.UUID(workspace_id)
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid workspace_id UUID format.")

    total = query.count()
    runs = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "runs": [_run_to_summary(r) for r in runs],
    }


@cockpit_router.get(
    "/runs/{run_id}",
    response_model=PipelineRunDetail,
    summary="Get pipeline run detail",
    description="Returns full detail for a single pipeline run including all node execution records.",
)
async def get_run(
    run_id: str = Path(..., description="Pipeline run UUID"),
    db: Session = Depends(get_db),
) -> PipelineRunDetail:
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id UUID format.")

    run = db.query(PipelineRun).filter(PipelineRun.id == run_uuid).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run '{run_id}' not found.")

    nodes = (
        db.query(PipelineNodeExecution)
        .filter(PipelineNodeExecution.run_id == run_uuid)
        .order_by(PipelineNodeExecution.node_order.asc())
        .all()
    )

    return PipelineRunDetail(
        id=str(run.id),
        status=run.status,
        campaign_id=str(run.campaign_id) if run.campaign_id else None,
        workspace_id=str(run.workspace_id) if run.workspace_id else None,
        initial_state=run.initial_state or {},
        final_state=run.final_state or {},
        error_message=run.error_message,
        started_at=_dt_str(run.started_at),
        completed_at=_dt_str(run.completed_at),
        nodes=[_node_to_schema(n) for n in nodes],
    )


@cockpit_router.get(
    "/runs/{run_id}/dag",
    response_model=DAGResponse,
    summary="Get DAG node statuses for visualization",
    description=(
        "Returns the status of every known pipeline node for a given run. "
        "Nodes that have not yet been reached are returned with status 'not_started'. "
        "Consumed by the frontend DAG graph renderer."
    ),
)
async def get_run_dag(
    run_id: str = Path(..., description="Pipeline run UUID"),
    db: Session = Depends(get_db),
) -> DAGResponse:
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id UUID format.")

    run = db.query(PipelineRun).filter(PipelineRun.id == run_uuid).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run '{run_id}' not found.")

    # Build a lookup from node_name → most recent execution record
    executions = (
        db.query(PipelineNodeExecution)
        .filter(PipelineNodeExecution.run_id == run_uuid)
        .order_by(PipelineNodeExecution.node_order.asc())
        .all()
    )
    exec_map: Dict[str, PipelineNodeExecution] = {}
    for ex in executions:
        # Last write wins for nodes that may have retried
        exec_map[ex.node_name] = ex

    dag_nodes: List[DAGNodeStatus] = []
    for node_name, order in sorted(
        pipeline_tracker.NODE_ORDER.items(), key=lambda x: x[1]
    ):
        if node_name in exec_map:
            ex = exec_map[node_name]
            dag_nodes.append(
                DAGNodeStatus(
                    node_name=node_name,
                    node_order=order,
                    status=ex.status,
                    duration_ms=ex.duration_ms or 0,
                    error_message=ex.error_message,
                )
            )
        else:
            dag_nodes.append(
                DAGNodeStatus(
                    node_name=node_name,
                    node_order=order,
                    status="not_started",
                    duration_ms=0,
                    error_message=None,
                )
            )

    return DAGResponse(
        run_id=run_id, run_status=run.status, nodes=dag_nodes
    )


# ─────────────────────────────────────────────────────────────────────────────
# Quarantine Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@cockpit_router.get(
    "/quarantine",
    response_model=Dict[str, Any],
    summary="List quarantined tasks",
    description="Returns paginated quarantined tasks. Filter by resolution_status.",
)
async def list_quarantined(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    resolution_status: Optional[str] = Query(
        None, description="Filter: 'pending', 'resumed', 'discarded'"
    ),
) -> Dict[str, Any]:
    query = db.query(QuarantinedTask).order_by(QuarantinedTask.created_at.desc())
    if resolution_status:
        query = query.filter(QuarantinedTask.resolution_status == resolution_status)
    total = query.count()
    tasks = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "tasks": [_qt_to_summary(t) for t in tasks],
    }


@cockpit_router.get(
    "/quarantine/{task_id}",
    response_model=QuarantinedTaskDetail,
    summary="Get quarantined task detail",
    description=(
        "Returns full detail for a quarantined task including the frozen state JSON "
        "and any edited state the operator has applied."
    ),
)
async def get_quarantined_task(
    task_id: str = Path(..., description="Quarantined task UUID"),
    db: Session = Depends(get_db),
) -> QuarantinedTaskDetail:
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task_id UUID format.")

    qt = db.query(QuarantinedTask).filter(QuarantinedTask.id == task_uuid).first()
    if not qt:
        raise HTTPException(status_code=404, detail=f"Quarantined task '{task_id}' not found.")
    return _qt_to_detail(qt)


@cockpit_router.put(
    "/quarantine/{task_id}/state",
    response_model=QuarantinedTaskDetail,
    summary="Edit frozen state JSON",
    description=(
        "Allows an operator to patch the editable state of a quarantined task. "
        "The original_state is preserved for audit. The edited_state will be used "
        "when the operator triggers a resume."
    ),
)
async def edit_frozen_state(
    task_id: str = Path(..., description="Quarantined task UUID"),
    body: EditFrozenStateRequest = ...,
    db: Session = Depends(get_db),
) -> QuarantinedTaskDetail:
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task_id UUID format.")

    qt = db.query(QuarantinedTask).filter(QuarantinedTask.id == task_uuid).first()
    if not qt:
        raise HTTPException(status_code=404, detail=f"Quarantined task '{task_id}' not found.")
    if qt.resolution_status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Task is already '{qt.resolution_status}' — state cannot be edited.",
        )
    qt.edited_state = body.edited_state
    db.commit()
    db.refresh(qt)
    logger.info(f"[COCKPIT] Frozen state updated for quarantine task {task_id}")
    return _qt_to_detail(qt)


@cockpit_router.post(
    "/quarantine/{task_id}/resume",
    summary="Force-resume from quarantined node",
    description=(
        "Re-invokes the autonomous pipeline starting from the quarantined node's "
        "edited_state. If no edited_state has been set, the original frozen_state "
        "is used. Marks the task as 'resumed'."
    ),
    response_model=Dict[str, Any],
)
async def resume_quarantined_task(
    task_id: str = Path(..., description="Quarantined task UUID"),
    body: ResumeQuarantineRequest = ...,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task_id UUID format.")

    qt = db.query(QuarantinedTask).filter(QuarantinedTask.id == task_uuid).first()
    if not qt:
        raise HTTPException(status_code=404, detail=f"Quarantined task '{task_id}' not found.")
    if qt.resolution_status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Task is already '{qt.resolution_status}' — cannot resume.",
        )

    # Determine which state to resume from
    resume_state: Dict[str, Any] = qt.edited_state or qt.frozen_state or {}

    # Ensure required orchestration fields are present
    resume_state.setdefault("workspace_id", body.workspace_id)
    if body.campaign_id:
        resume_state.setdefault("campaign_id", body.campaign_id)
    if body.product_id:
        resume_state.setdefault("product_id", body.product_id)

    # Mark as resumed before triggering so UI reflects immediately
    qt.resolution_status = "resumed"
    qt.resolved_by = body.resumed_by
    qt.resolved_at = datetime.now(timezone.utc)
    db.commit()

    # Trigger autonomous generation asynchronously
    try:
        from core.bandit_orchestrator import trigger_autonomous_generation
        new_run_result = await trigger_autonomous_generation(
            workspace_id=resume_state.get("workspace_id", body.workspace_id),
            campaign_id=resume_state.get("campaign_id", body.campaign_id or ""),
            product_id=resume_state.get("product_id", body.product_id or ""),
            db=db,
        )
        logger.info(
            f"[COCKPIT] Quarantine task {task_id} resumed successfully by {body.resumed_by}"
        )
        return {
            "status": "resumed",
            "task_id": task_id,
            "resumed_by": body.resumed_by,
            "new_run_result_keys": list(new_run_result.keys()) if new_run_result else [],
        }
    except Exception as exc:
        logger.error(f"[COCKPIT] Failed to resume quarantine task {task_id}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Resume triggered but pipeline failed: {str(exc)}",
        )


@cockpit_router.post(
    "/quarantine/{task_id}/discard",
    summary="Discard a quarantined task",
    description=(
        "Marks the quarantined task as discarded without resuming the pipeline. "
        "Use when the task is stale, a duplicate, or caused by an expected transient error."
    ),
    response_model=Dict[str, Any],
)
async def discard_quarantined_task(
    task_id: str = Path(..., description="Quarantined task UUID"),
    body: DiscardQuarantineRequest = ...,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task_id UUID format.")

    qt = db.query(QuarantinedTask).filter(QuarantinedTask.id == task_uuid).first()
    if not qt:
        raise HTTPException(status_code=404, detail=f"Quarantined task '{task_id}' not found.")
    if qt.resolution_status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Task is already '{qt.resolution_status}' — cannot discard.",
        )

    qt.resolution_status = "discarded"
    qt.resolved_by = body.discarded_by
    qt.resolved_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"[COCKPIT] Quarantine task {task_id} discarded by {body.discarded_by}")
    return {"status": "discarded", "task_id": task_id, "discarded_by": body.discarded_by}


# ─────────────────────────────────────────────────────────────────────────────
# Kill Switch Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@cockpit_router.get(
    "/kill-switch",
    response_model=KillSwitchStatus,
    summary="Get kill switch status",
    description=(
        "Returns the current state of the system kill switch. "
        "When is_active=true, the publisher_node and all social Celery tasks "
        "are blocked from making external API calls."
    ),
)
async def get_kill_switch_status(
    workspace_id: Optional[str] = Query(None, description="Workspace UUID to scope the query"),
    db: Session = Depends(get_db),
) -> KillSwitchStatus:
    query = db.query(SystemKillSwitch)
    if workspace_id:
        try:
            query = query.filter(
                SystemKillSwitch.workspace_id == uuid.UUID(workspace_id)
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid workspace_id UUID format.")

    # Return the most recently updated record
    ks = query.order_by(SystemKillSwitch.updated_at.desc()).first()
    if not ks:
        # No record exists — return safe default
        return KillSwitchStatus(
            is_active=False,
            activated_by=None,
            activated_at=None,
            deactivated_at=None,
            reason="No kill switch record found — system operating normally.",
            workspace_id=workspace_id,
        )

    return KillSwitchStatus(
        is_active=ks.is_active,
        activated_by=ks.activated_by,
        activated_at=_dt_str(ks.activated_at),
        deactivated_at=_dt_str(ks.deactivated_at),
        reason=ks.reason,
        workspace_id=str(ks.workspace_id) if ks.workspace_id else None,
    )


@cockpit_router.post(
    "/kill-switch/activate",
    response_model=KillSwitchStatus,
    summary="Activate the kill switch",
    description=(
        "Immediately blocks all outbound Facebook Ads API calls and social publishing. "
        "The internal LangGraph pipeline continues for analysis. "
        "This action is broadcast via WebSocket to all connected cockpit clients."
    ),
)
async def activate_kill_switch(
    body: ActivateKillSwitchRequest,
    db: Session = Depends(get_db),
) -> KillSwitchStatus:
    try:
        pipeline_tracker.activate_kill_switch(
            workspace_id=body.workspace_id,
            activated_by=body.activated_by,
            reason=body.reason,
        )
    except Exception as exc:
        logger.error(f"Kill switch activation failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Kill switch activation failed: {exc}")

    # Re-read from DB for the response
    ks = db.query(SystemKillSwitch).filter(
        SystemKillSwitch.workspace_id == uuid.UUID(body.workspace_id)
    ).first()
    if not ks:
        raise HTTPException(status_code=500, detail="Kill switch record not found after activation.")

    return KillSwitchStatus(
        is_active=ks.is_active,
        activated_by=ks.activated_by,
        activated_at=_dt_str(ks.activated_at),
        deactivated_at=_dt_str(ks.deactivated_at),
        reason=ks.reason,
        workspace_id=str(ks.workspace_id) if ks.workspace_id else None,
    )


@cockpit_router.post(
    "/kill-switch/deactivate",
    response_model=KillSwitchStatus,
    summary="Deactivate the kill switch",
    description=(
        "Re-enables external API calls for all publisher nodes and social tasks. "
        "This action is broadcast via WebSocket to all connected cockpit clients."
    ),
)
async def deactivate_kill_switch(
    body: DeactivateKillSwitchRequest,
    db: Session = Depends(get_db),
) -> KillSwitchStatus:
    try:
        pipeline_tracker.deactivate_kill_switch(
            workspace_id=body.workspace_id,
            deactivated_by=body.deactivated_by,
        )
    except Exception as exc:
        logger.error(f"Kill switch deactivation failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Kill switch deactivation failed: {exc}")

    ks = db.query(SystemKillSwitch).filter(
        SystemKillSwitch.workspace_id == uuid.UUID(body.workspace_id)
    ).first()
    if not ks:
        raise HTTPException(status_code=500, detail="Kill switch record not found after deactivation.")

    return KillSwitchStatus(
        is_active=ks.is_active,
        activated_by=ks.activated_by,
        activated_at=_dt_str(ks.activated_at),
        deactivated_at=_dt_str(ks.deactivated_at),
        reason=ks.reason,
        workspace_id=str(ks.workspace_id) if ks.workspace_id else None,
    )
