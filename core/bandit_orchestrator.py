# core/bandit_orchestrator.py
"""
Bandit Orchestrator — The MAB (Multi-Armed Bandit) Computation Layer.

Responsibilities:
    1. Reward calculation from campaign analytics metrics.
    2. Cold-start resolution via SQL-based statistical baseline.
    3. Epsilon-Greedy MAB prior computation (80% Exploit / 20% Explore).
    4. Autonomous pipeline orchestration via ``trigger_autonomous_generation()``.

Cockpit Integration (Phase 6):
    - Kill switch is checked before graph.ainvoke() — raises if active.
    - Execution mode (shadow / live) is read from pipeline_tracker and injected into state.
    - PipelineRun records are created, completed, or failed via pipeline_tracker.
    - ``_run_id`` and ``_execution_mode`` are injected into initial_state for node tracking.
"""
import random
import logging
import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from core.models import MarketingCampaign, CampaignAnalytics, AIInsightPending
from core import pipeline_tracker
from graphs.main_router import graph

logger = logging.getLogger("bandit_orchestrator")
logger.setLevel(logging.INFO)

ANGLES = ["Fear", "Emotion", "Logic", "Social Proof", "Urgency", "Curiosity"]

def calculate_reward(metrics: Dict[str, Any], objective: str) -> float:
    """
    CMO-CTO Aligned Reward Calculation formula.
    Prevents bidding conflict while providing clear metric direction.

    Args:
        metrics:   Dict with keys: impressions, clicks, conversions, spend.
        objective: 'BRAND_AWARENESS' or 'LEAD_GEN'.

    Returns:
        Scalar reward value. Higher = better performing angle.
    """
    try:
        impressions = float(metrics.get("impressions") or 0)
        clicks = float(metrics.get("clicks") or 0)
        conversions = float(metrics.get("conversions") or 0)
        spend = float(metrics.get("spend") or 0)
        
        ctr = clicks / impressions if impressions > 0 else 0.0
        cpm = (spend / impressions) * 1000 if impressions > 0 else 0.0
        cpa = spend / conversions if conversions > 0 else 0.0

        if objective == "BRAND_AWARENESS":
            return (impressions / 1000.0) * 0.5 - (cpm * 0.3) + (ctr * 0.2)
        elif objective == "LEAD_GEN":
            if cpa <= 0:
                return 0.0
            return 1.0 / cpa
    except Exception as e:
        logger.error(f"Error calculating reward: {e}. Fallback to 0.0")
        return 0.0
    return 0.0

def solve_cold_start(db: Session, objective: str) -> Dict[str, Any]:
    """
    SQL-based Cold Start Solver.
    Avoids semantic RAG searches for metrics, using statistical campaign averages instead.

    Args:
        db:        Active SQLAlchemy session.
        objective: Campaign objective string.

    Returns:
        Dict of average metrics (impressions, clicks, conversions, spend).
    """
    logger.info("Solving Cold Start via SQL average metrics...")
    avg_metrics = {
        "impressions": 10000.0,
        "clicks": 500.0,
        "conversions": 10.0,
        "spend": 2000000.0
    }
    try:
        query = text("""
            SELECT 
                AVG(impressions) as avg_imp,
                AVG(clicks) as avg_clk,
                AVG(conversions) as avg_conv,
                AVG(spend) as avg_spend
            FROM campaign_analytics
        """)
        res = db.execute(query).fetchone()
        if res:
            avg_metrics["impressions"] = float(res[0]) if res[0] is not None else 10000.0
            avg_metrics["clicks"] = float(res[1]) if res[1] is not None else 500.0
            avg_metrics["conversions"] = float(res[2]) if res[2] is not None else 10.0
            avg_metrics["spend"] = float(res[3]) if res[3] is not None else 2000000.0
    except Exception as e:
        logger.error(f"Cold-start SQL baseline calculation failed: {e}. Falling back to default uniform metrics.")
        
    logger.info(f"Cold start baseline metrics calculated: {avg_metrics}")
    return avg_metrics

def compute_mab_beliefs(db: Session, campaign_id: str, objective: str, epsilon: float = 0.2) -> Dict[str, Any]:
    """
    Runs Epsilon-Greedy or Thompson Sampling mathematics to formulate beliefs/priors.
    Maps Content Generation Output mix: 80% Exploit (proven angles) / 20% Explore (wildcard).

    Args:
        db:          Active SQLAlchemy session.
        campaign_id: UUID string of the target campaign.
        objective:   'BRAND_AWARENESS' or 'LEAD_GEN'.
        epsilon:     Exploration probability (default 0.2 → 20% Explore).

    Returns:
        Dict with keys: beliefs (Dict[angle, weight]), metrics (Dict), cold_start (bool).
    """
    logger.info(f"Computing MAB priors for campaign_id: {campaign_id}")
    
    # Fetch historical metrics for this campaign
    history = db.query(CampaignAnalytics).filter_by(campaign_id=uuid.UUID(campaign_id)).all()
    
    if not history:
        # Resolve Cold Start via SQL Baseline averages
        baseline_metrics = solve_cold_start(db, objective)
        # Seed initial beliefs equally
        beliefs = {angle: 1.0 / len(ANGLES) for angle in ANGLES}
        return {
            "beliefs": beliefs,
            "metrics": baseline_metrics,
            "cold_start": True
        }
    
    # Calculate rewards for each angle based on historical data
    angle_metrics = {angle: {"impressions": 0, "clicks": 0, "conversions": 0, "spend": 0.0} for angle in ANGLES}
    
    for row in history:
        # Simple heuristic to classify historical metrics into angles
        angle = ANGLES[hash(row.id) % len(ANGLES)]
        angle_metrics[angle]["impressions"] += row.impressions
        angle_metrics[angle]["clicks"] += row.clicks
        angle_metrics[angle]["conversions"] += row.conversions
        angle_metrics[angle]["spend"] += float(row.spend)
        
    rewards = {}
    for angle in ANGLES:
        rewards[angle] = calculate_reward(angle_metrics[angle], objective)
        
    # Epsilon-Greedy MAB Output mix (80% Exploit, 20% Explore)
    sorted_angles = sorted(rewards.items(), key=lambda x: x[1], reverse=True)
    best_angle = sorted_angles[0][0]
    
    beliefs = {}
    for angle in ANGLES:
        if angle == best_angle:
            # High weight allocated to exploit (80%)
            beliefs[angle] = 0.8
        else:
            # Explorer share (20%) divided among other 5 angles
            beliefs[angle] = 0.2 / (len(ANGLES) - 1)
            
    # Compile aggregate current campaign metrics
    agg_metrics = {
        "impressions": sum(v["impressions"] for v in angle_metrics.values()),
        "clicks": sum(v["clicks"] for v in angle_metrics.values()),
        "conversions": sum(v["conversions"] for v in angle_metrics.values()),
        "spend": sum(v["spend"] for v in angle_metrics.values())
    }
    
    return {
        "beliefs": beliefs,
        "metrics": agg_metrics,
        "cold_start": False
    }

async def trigger_autonomous_generation(
    workspace_id: str,
    campaign_id: str,
    product_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Orchestration layer. Computes MAB beliefs, creates a pipeline run record, triggers
    LangGraph, and terminates immediately (stateless fire-and-observe pattern).

    Cockpit Integration:
        1. Kill switch check: raises ``RuntimeError`` if the switch is active.
        2. Reads current execution mode from ``pipeline_tracker.get_execution_mode()``.
        3. Creates a ``PipelineRun`` record via ``pipeline_tracker.start_run()``.
        4. Injects ``_run_id`` and ``_execution_mode`` into ``initial_state`` for node tracking.
        5. Calls ``pipeline_tracker.complete_run()`` on success.
        6. Calls ``pipeline_tracker.fail_run()`` on exception, then re-raises.

    Args:
        workspace_id: UUID string of the workspace.
        campaign_id:  UUID string of the campaign.
        product_id:   UUID string of the product/service.
        db:           Active SQLAlchemy session (used only for pre-flight queries here).

    Returns:
        result_state: The final AgencyState dict returned by graph.ainvoke().

    Raises:
        RuntimeError: If the kill switch is active.
        ValueError:   If the campaign is not found in the database.
    """
    logger.info("Starting autonomous generation loop...")

    # ── Kill Switch Pre-flight ─────────────────────────────────────────────────
    if pipeline_tracker.is_kill_switch_active(workspace_id=workspace_id):
        msg = (
            "[KILL SWITCH] Autonomous generation is BLOCKED. "
            "The system kill switch is currently active. "
            "Deactivate it via the Cockpit API before retrying."
        )
        logger.error(msg)
        raise RuntimeError(msg)

    # ── Read Current Execution Mode ────────────────────────────────────────────
    execution_mode = pipeline_tracker.get_execution_mode()
    logger.info(f"[COCKPIT] Execution mode for this run: {execution_mode.upper()}")

    # ── Fetch campaign metadata ────────────────────────────────────────────────
    campaign = db.query(MarketingCampaign).filter_by(id=uuid.UUID(campaign_id)).first()
    if not campaign:
        raise ValueError(f"Campaign with ID {campaign_id} not found.")
        
    objective = campaign.campaign_type or "LEAD_GEN"
    if objective not in ["BRAND_AWARENESS", "LEAD_GEN"]:
        objective = "LEAD_GEN"
        
    # ── Compute MAB Priors ─────────────────────────────────────────────────────
    mab_result = compute_mab_beliefs(db, campaign_id, objective)
    priors = mab_result["beliefs"]
    metrics = mab_result["metrics"]
    
    # ── Build Initial State ────────────────────────────────────────────────────
    initial_state = {
        "workspace_id": workspace_id,
        "campaign_id": campaign_id,
        "product_id": product_id,
        "campaign_objective": objective,
        "current_metrics": metrics,
        "current_beliefs": priors,
        "sop_stage": "scoring",
        "selected_actions": [],
        "generated_variants": [],
        "sandbox_feedbacks": [],
        # Cockpit fields — consumed by autonomous_nodes.py for run tracking
        "_execution_mode": execution_mode,
    }

    # ── Create Pipeline Run Record ─────────────────────────────────────────────
    run_id = pipeline_tracker.start_run(
        workspace_id=workspace_id,
        campaign_id=campaign_id,
        execution_mode=execution_mode,
        initial_state=initial_state,
    )
    # Inject run_id so every node can call pipeline_tracker.start_node(run_id, ...)
    initial_state["_run_id"] = run_id
    
    config = {
        "configurable": {
            "thread_id": f"autonomous_{campaign_id}_{uuid.uuid4().hex[:6]}",
            "workspace_id": workspace_id,
            "product_id": product_id
        }
    }
    
    # ── Invoke LangGraph Pipeline ──────────────────────────────────────────────
    logger.info(f"[COCKPIT] Invoking LangGraph pipeline (run_id={run_id})...")
    try:
        result_state = await graph.ainvoke(initial_state, config=config)
        pipeline_tracker.complete_run(run_id, dict(result_state))
        logger.info(
            f"[COCKPIT] Stateless LangGraph execution completed successfully (run_id={run_id})."
        )
        return result_state

    except Exception as exc:
        error_msg = str(exc)
        logger.error(
            f"[COCKPIT] LangGraph pipeline FAILED (run_id={run_id}): {error_msg}"
        )
        pipeline_tracker.fail_run(run_id, error_msg)
        raise
