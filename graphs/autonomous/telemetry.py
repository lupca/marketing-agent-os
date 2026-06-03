# graphs/autonomous/telemetry.py
import logging
import time
import functools
from core import pipeline_tracker
from graphs.supervisor.state import AgencyState

logger = logging.getLogger("autonomous_nodes")

def instrument_node(node_name: str):
    """
    Decorator to instrument LangGraph nodes with Pipeline Tracker telemetry.
    Eliminates redundant telemetry/logging boilerplate across all nodes.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(state: AgencyState, *args, **kwargs) -> dict:
            run_id = state.get("_run_id")
            node_exec_id = None
            t0 = time.time()

            if run_id:
                try:
                    node_exec_id = pipeline_tracker.start_node(run_id, node_name, dict(state))
                except Exception as track_err:
                    logger.warning(f"[TRACKER] start_node failed for '{node_name}': {track_err}")

            try:
                result = func(state, *args, **kwargs)
                
                if node_exec_id:
                    duration = int((time.time() - t0) * 1000)
                    try:
                        pipeline_tracker.complete_node(node_exec_id, result, duration_ms=duration)
                    except Exception as track_err:
                        logger.warning(f"[TRACKER] complete_node failed for '{node_name}': {track_err}")
                return result
            except Exception as exc:
                duration = int((time.time() - t0) * 1000)
                if node_exec_id:
                    try:
                        pipeline_tracker.fail_node(node_exec_id, str(exc), duration_ms=duration)
                    except Exception as track_err:
                        logger.warning(f"[TRACKER] fail_node failed for '{node_name}': {track_err}")
                raise
        return wrapper
    return decorator
