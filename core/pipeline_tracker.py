# core/pipeline_tracker.py
"""
Pipeline Tracker Service — The Autopilot Cockpit's observability engine.

Instruments every LangGraph node execution with timing, I/O capture, and real-time
WebSocket broadcasting. All public functions are intentionally synchronous so they
can be called from plain (non-async) node functions without an event-loop dance.

Usage in a LangGraph node:
    from core import pipeline_tracker

    def my_node(state: AgencyState) -> dict:
        run_id = state.get("_run_id")
        t0 = time.time()
        node_exec_id = pipeline_tracker.start_node(run_id, "my_node", dict(state))
        try:
            result = do_work(state)
            duration = int((time.time() - t0) * 1000)
            pipeline_tracker.complete_node(node_exec_id, result, duration_ms=duration)
            return result
        except Exception as exc:
            duration = int((time.time() - t0) * 1000)
            pipeline_tracker.fail_node(node_exec_id, str(exc), duration_ms=duration)
            raise
"""
import uuid
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.dependencies import get_session
from core.pipeline_models import (
    PipelineRun,
    PipelineNodeExecution,
    QuarantinedTask,
    SystemKillSwitch,
)

logger = logging.getLogger("pipeline_tracker")

# ─────────────────────────────────────────────────────────────────────────────
# Module-level singletons
# ─────────────────────────────────────────────────────────────────────────────

# Set by app.py startup event via set_cockpit_broadcaster()
_cockpit_broadcaster = None

# In-process execution mode — persisted to DB on every change
_execution_mode_cache: Dict[str, str] = {"mode": "live"}


# ─────────────────────────────────────────────────────────────────────────────
# Broadcaster Registration
# ─────────────────────────────────────────────────────────────────────────────

def set_cockpit_broadcaster(broadcaster: Any) -> None:
    """
    Register the WebSocket broadcaster instance at application startup.

    This must be called once from the FastAPI startup event handler so that
    cockpit events are pushed to connected frontend clients in real-time.

    Args:
        broadcaster: An object that exposes a coroutine ``broadcast(message: str)``
                     and a synchronous ``disconnect(websocket)`` method.
    """
    global _cockpit_broadcaster
    _cockpit_broadcaster = broadcaster
    logger.info("[COCKPIT] WebSocket broadcaster registered.")


# ─────────────────────────────────────────────────────────────────────────────
# Internal Broadcast Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _broadcast_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Async coroutine that serializes and sends a structured cockpit event to all
    connected WebSocket clients via the registered broadcaster.

    Args:
        event_type: Short event label consumed by the frontend (e.g. 'node_start').
        data:       Arbitrary JSON-serializable payload dict.
    """
    if _cockpit_broadcaster is None:
        return
    try:
        payload = json.dumps(
            {
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
            },
            default=str,
        )
        await _cockpit_broadcaster.broadcast(payload)
    except Exception as exc:
        logger.warning(f"[COCKPIT] Failed to broadcast event '{event_type}': {exc}")


def broadcast_event_sync(event_type: str, data: Dict[str, Any]) -> None:
    """
    Synchronous broadcast wrapper safe to call from non-async node functions.

    Behaviour:
        - If an event loop is already running (standard FastAPI / uvicorn context),
          schedules the coroutine via ``asyncio.run_coroutine_threadsafe``.
        - If no loop is running (test or CLI context), falls back to
          ``asyncio.run()`` on a fresh coroutine.
        - Never raises — broadcast failures are logged as warnings only.

    Args:
        event_type: Short event label.
        data:       JSON-serializable payload dict.
    """
    if _cockpit_broadcaster is None:
        return
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                _broadcast_event(event_type, data), loop
            )
        else:
            asyncio.run(_broadcast_event(event_type, data))
    except Exception as exc:
        logger.warning(f"[COCKPIT] Sync broadcast failed for '{event_type}': {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Execution Mode
# ─────────────────────────────────────────────────────────────────────────────

def get_execution_mode() -> str:
    """
    Return the current global execution mode.

    Returns:
        'shadow' — pipeline runs but no external publishing occurs.
        'live'   — full autonomous publishing to Facebook Ads / social platforms.
    """
    return _execution_mode_cache.get("mode", "shadow")


def set_execution_mode(mode: str) -> None:
    """
    Change the global execution mode for all subsequent pipeline runs.

    Args:
        mode: Must be either 'shadow' or 'live'.

    Raises:
        ValueError: If an invalid mode string is provided.
    """
    if mode not in ("shadow", "live"):
        raise ValueError(
            f"Invalid execution mode '{mode}'. Accepted values: 'shadow', 'live'."
        )
    _execution_mode_cache["mode"] = mode
    logger.info(f"[COCKPIT] Execution mode changed → {mode.upper()}")
    broadcast_event_sync("mode_change", {"mode": mode})


# ─────────────────────────────────────────────────────────────────────────────
# Kill Switch
# ─────────────────────────────────────────────────────────────────────────────

def is_kill_switch_active(workspace_id: Optional[str] = None) -> bool:
    """
    Query the database for the authoritative kill switch state.

    Fail-open design: if the database is unreachable, returns False so the
    pipeline is not accidentally frozen by an infrastructure outage.

    Args:
        workspace_id: Optional UUID string to scope the check to a specific workspace.
                      If None, checks for ANY active kill switch globally.

    Returns:
        True if the kill switch is currently active, False otherwise.
    """
    try:
        with get_session() as db:
            query = db.query(SystemKillSwitch).filter(
                SystemKillSwitch.is_active.is_(True)
            )
            if workspace_id:
                query = query.filter(
                    SystemKillSwitch.workspace_id == uuid.UUID(str(workspace_id))
                )
            return query.first() is not None
    except Exception as exc:
        logger.error(f"[COCKPIT] Kill switch DB check failed (fail-open): {exc}")
        return False  # Fail-open: allow execution if DB is unreachable


def activate_kill_switch(
    workspace_id: str, activated_by: str, reason: str
) -> Dict[str, Any]:
    """
    Activate the kill switch for a given workspace. This immediately blocks
    all outbound Facebook Ads API calls and social publishing in the
    publisher_node and any Celery social tasks.

    The internal LangGraph pipeline (scoring → insight) continues to run
    for analysis purposes — only external I/O is gated.

    Args:
        workspace_id:  UUID string of the target workspace.
        activated_by:  Human-readable identifier of who triggered the activation
                       (e.g. user email, 'system', 'circuit_breaker').
        reason:        Human-readable explanation for audit trail.

    Returns:
        Dict with keys: is_active, activated_by, reason.
    """
    with get_session() as db:
        ks = db.query(SystemKillSwitch).filter(
            SystemKillSwitch.workspace_id == uuid.UUID(workspace_id)
        ).first()
        if not ks:
            ks = SystemKillSwitch(workspace_id=uuid.UUID(workspace_id))
            db.add(ks)
        ks.is_active = True
        ks.activated_by = activated_by
        ks.activated_at = datetime.now(timezone.utc)
        ks.deactivated_at = None
        ks.reason = reason
        db.commit()

    logger.critical(
        f"[KILL SWITCH] ⛔ ACTIVATED by '{activated_by}'. Reason: {reason}"
    )
    broadcast_event_sync(
        "kill_switch",
        {
            "is_active": True,
            "activated_by": activated_by,
            "reason": reason,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"is_active": True, "activated_by": activated_by, "reason": reason}


def deactivate_kill_switch(
    workspace_id: str, deactivated_by: str
) -> Dict[str, Any]:
    """
    Deactivate the kill switch, resuming normal outbound API operations.

    Args:
        workspace_id:    UUID string of the target workspace.
        deactivated_by:  Human-readable identifier of who cleared the switch.

    Returns:
        Dict with key: is_active (always False on success).
    """
    with get_session() as db:
        ks = db.query(SystemKillSwitch).filter(
            SystemKillSwitch.workspace_id == uuid.UUID(workspace_id)
        ).first()
        if ks:
            ks.is_active = False
            ks.deactivated_at = datetime.now(timezone.utc)
            db.commit()

    logger.info(f"[KILL SWITCH] ✅ Deactivated by '{deactivated_by}'.")
    broadcast_event_sync(
        "kill_switch",
        {
            "is_active": False,
            "deactivated_by": deactivated_by,
            "deactivated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"is_active": False}


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Run Tracking
# ─────────────────────────────────────────────────────────────────────────────

def start_run(
    workspace_id: Optional[str],
    campaign_id: Optional[str],
    execution_mode: str,
    initial_state: Dict[str, Any],
) -> str:
    """
    Create a new PipelineRun record in the database and broadcast a run_start event.

    Args:
        workspace_id:    UUID string of the workspace (may be None).
        campaign_id:     UUID string of the campaign (may be None).
        execution_mode:  'shadow' or 'live'.
        initial_state:   The AgencyState dict passed to graph.ainvoke().

    Returns:
        run_id: UUID string of the newly created PipelineRun row.
    """
    with get_session() as db:
        run = PipelineRun(
            workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
            campaign_id=uuid.UUID(campaign_id) if campaign_id else None,
            execution_mode=execution_mode,
            status="running",
            initial_state=_sanitize_state(initial_state),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = str(run.id)

    logger.info(
        f"[COCKPIT] 🚀 Pipeline run started: {run_id} (mode={execution_mode})"
    )
    broadcast_event_sync(
        "run_start",
        {
            "run_id": run_id,
            "execution_mode": execution_mode,
            "campaign_id": campaign_id,
            "workspace_id": workspace_id,
        },
    )
    return run_id


def complete_run(run_id: str, final_state: Dict[str, Any]) -> None:
    """
    Mark a pipeline run as successfully completed and persist the final state.

    Args:
        run_id:      UUID string of the PipelineRun to update.
        final_state: The AgencyState dict returned from graph.ainvoke().
    """
    with get_session() as db:
        run = db.query(PipelineRun).filter(
            PipelineRun.id == uuid.UUID(run_id)
        ).first()
        if run:
            run.status = "completed"
            run.final_state = _sanitize_state(final_state)
            run.completed_at = datetime.now(timezone.utc)
            db.commit()

    logger.info(f"[COCKPIT] ✅ Pipeline run completed: {run_id}")
    broadcast_event_sync("run_complete", {"run_id": run_id, "status": "completed"})


def fail_run(run_id: str, error_message: str) -> None:
    """
    Mark a pipeline run as failed with an error message.

    Args:
        run_id:        UUID string of the PipelineRun to update.
        error_message: Stringified exception or error description.
    """
    with get_session() as db:
        run = db.query(PipelineRun).filter(
            PipelineRun.id == uuid.UUID(run_id)
        ).first()
        if run:
            run.status = "failed"
            run.error_message = error_message
            run.completed_at = datetime.now(timezone.utc)
            db.commit()

    logger.error(f"[COCKPIT] ❌ Pipeline run failed: {run_id} — {error_message}")
    broadcast_event_sync(
        "run_fail", {"run_id": run_id, "error": error_message, "status": "failed"}
    )


# ─────────────────────────────────────────────────────────────────────────────
# Node Execution Tracking
# ─────────────────────────────────────────────────────────────────────────────

# Canonical node order for DAG visualization (matches LangGraph pipeline definition)
NODE_ORDER: Dict[str, int] = {
    "scoring": 1,
    "selector": 2,
    "creative_generation": 3,
    "guardian_sandbox": 4,
    "insight_generator": 5,
    "publisher": 6,
}


def start_node(
    run_id: str, node_name: str, input_state: Dict[str, Any]
) -> str:
    """
    Record the start of a node execution and broadcast a node_start event.

    Args:
        run_id:      UUID string of the parent PipelineRun.
        node_name:   Name of the LangGraph node being executed.
        input_state: AgencyState dict as received by this node.

    Returns:
        node_exec_id: UUID string of the newly created PipelineNodeExecution row.
    """
    with get_session() as db:
        node_exec = PipelineNodeExecution(
            run_id=uuid.UUID(run_id),
            node_name=node_name,
            node_order=NODE_ORDER.get(node_name, 99),
            status="running",
            input_state=_sanitize_state(input_state),
            started_at=datetime.now(timezone.utc),
        )
        db.add(node_exec)
        db.commit()
        db.refresh(node_exec)
        node_exec_id = str(node_exec.id)

    logger.info(f"[COCKPIT] ▶ Node '{node_name}' started (run={run_id})")
    broadcast_event_sync(
        "node_start",
        {
            "run_id": run_id,
            "node_execution_id": node_exec_id,
            "node_name": node_name,
            "node_order": NODE_ORDER.get(node_name, 99),
        },
    )
    return node_exec_id


def complete_node(
    node_exec_id: str,
    output_state: Dict[str, Any],
    duration_ms: int = 0,
    retry_count: int = 0,
) -> None:
    """
    Mark a node execution as successfully completed.

    Args:
        node_exec_id: UUID string of the PipelineNodeExecution row.
        output_state: The dict returned by the node function.
        duration_ms:  Wall-clock duration of the node in milliseconds.
        retry_count:  Number of retry attempts that occurred before success.
    """
    run_id = None
    node_name = None
    with get_session() as db:
        node_exec = db.query(PipelineNodeExecution).filter(
            PipelineNodeExecution.id == uuid.UUID(node_exec_id)
        ).first()
        if node_exec:
            node_exec.status = "completed"
            node_exec.output_state = _sanitize_state(output_state)
            node_exec.duration_ms = duration_ms
            node_exec.retry_count = retry_count
            node_exec.completed_at = datetime.now(timezone.utc)
            run_id = str(node_exec.run_id)
            node_name = node_exec.node_name
            db.commit()

    logger.info(
        f"[COCKPIT] ✓ Node '{node_name}' completed ({duration_ms}ms, run={run_id})"
    )
    broadcast_event_sync(
        "node_complete",
        {
            "node_execution_id": node_exec_id,
            "run_id": run_id,
            "node_name": node_name,
            "duration_ms": duration_ms,
            "status": "completed",
        },
    )


def fail_node(
    node_exec_id: str, error_message: str, duration_ms: int = 0
) -> None:
    """
    Mark a node execution as failed.

    Args:
        node_exec_id:  UUID string of the PipelineNodeExecution row.
        error_message: Stringified exception caught during node execution.
        duration_ms:   Wall-clock duration before failure in milliseconds.
    """
    run_id = None
    node_name = None
    with get_session() as db:
        node_exec = db.query(PipelineNodeExecution).filter(
            PipelineNodeExecution.id == uuid.UUID(node_exec_id)
        ).first()
        if node_exec:
            node_exec.status = "failed"
            node_exec.error_message = error_message
            node_exec.duration_ms = duration_ms
            node_exec.completed_at = datetime.now(timezone.utc)
            run_id = str(node_exec.run_id)
            node_name = node_exec.node_name
            db.commit()

    logger.warning(
        f"[COCKPIT] ✗ Node '{node_name}' FAILED (run={run_id}): {error_message}"
    )
    broadcast_event_sync(
        "node_fail",
        {
            "node_execution_id": node_exec_id,
            "run_id": run_id,
            "node_name": node_name,
            "error": error_message,
            "status": "failed",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Quarantine
# ─────────────────────────────────────────────────────────────────────────────

def quarantine_task(
    run_id: str,
    node_name: str,
    frozen_state: Dict[str, Any],
    reason: str,
) -> str:
    """
    Move a pipeline task into quarantine. The pipeline run is marked as 'quarantined'.
    Engineers can inspect and edit the frozen_state via the Cockpit UI, then force-resume.

    Args:
        run_id:       UUID string of the parent PipelineRun.
        node_name:    Node at which execution was halted.
        frozen_state: Full AgencyState at the point of quarantine.
        reason:       Human-readable explanation for quarantine trigger.

    Returns:
        quarantine_task_id: UUID string of the created QuarantinedTask row.
    """
    with get_session() as db:
        qt = QuarantinedTask(
            run_id=uuid.UUID(run_id) if run_id else None,
            node_name=node_name,
            frozen_state=_sanitize_state(frozen_state),
            original_state=_sanitize_state(frozen_state),  # immutable copy
            quarantine_reason=reason,
            resolution_status="pending",
        )
        db.add(qt)
        # Cascade status to the parent run
        if run_id:
            run = db.query(PipelineRun).filter(
                PipelineRun.id == uuid.UUID(run_id)
            ).first()
            if run:
                run.status = "quarantined"
        db.commit()
        db.refresh(qt)
        qt_id = str(qt.id)

    logger.warning(
        f"[QUARANTINE] 🔒 Task quarantined — run={run_id}, node={node_name}, reason={reason}"
    )
    broadcast_event_sync(
        "quarantine",
        {
            "quarantine_id": qt_id,
            "run_id": run_id,
            "node_name": node_name,
            "reason": reason,
        },
    )
    return qt_id


# ─────────────────────────────────────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_state(state: Any) -> Dict[str, Any]:
    """
    Ensure a state dict is JSON-serializable before storing in JSONB columns.

    Strategy:
        - Non-dict inputs return an empty dict (defensive).
        - Each value is attempted via json.dumps; on failure the value is
          replaced by its str() representation.
        - This prevents SQLAlchemy JSONB type errors from unserializable objects
          (e.g. SQLAlchemy model instances, numpy arrays).

    Args:
        state: Any value — expected to be a dict.

    Returns:
        A fully JSON-serializable dict safe for JSONB storage.
    """
    if not isinstance(state, dict):
        return {}
    result: Dict[str, Any] = {}
    for k, v in state.items():
        try:
            json.dumps(v, default=str)
            result[k] = v
        except (TypeError, ValueError):
            result[k] = str(v)
    return result
