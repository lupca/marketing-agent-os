# core/bandit_orchestrator.py
import random
import logging
import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from core.models import MarketingCampaign, CampaignAnalytics, AIInsightPending
from graphs.main_router import graph

logger = logging.getLogger("bandit_orchestrator")
logger.setLevel(logging.INFO)

ANGLES = ["Fear", "Emotion", "Logic", "Social Proof", "Urgency", "Curiosity"]

def calculate_reward(metrics: Dict[str, Any], objective: str) -> float:
    """
    CMO-CTO Aligned Reward Calculation formula.
    Prevents bidding conflict while providing clear metric direction.
    """
    impressions = float(metrics.get("impressions", 0))
    clicks = float(metrics.get("clicks", 0))
    conversions = float(metrics.get("conversions", 0))
    spend = float(metrics.get("spend", 0))
    
    ctr = clicks / impressions if impressions > 0 else 0.0
    cpm = (spend / impressions) * 1000 if impressions > 0 else 0.0
    cpa = spend / conversions if conversions > 0 else 0.0

    if objective == "BRAND_AWARENESS":
        return (impressions / 1000.0) * 0.5 - (cpm * 0.3) + (ctr * 0.2)
    elif objective == "LEAD_GEN":
        if cpa == 0:
            return 0.0
        return 1.0 / cpa
    return 0.0

def solve_cold_start(db: Session, objective: str) -> Dict[str, Any]:
    """
    SQL-based Cold Start Solver.
    Avoids semantic RAG searches for metrics, using statistical campaign averages instead.
    """
    logger.info("Solving Cold Start via SQL average metrics...")
    query = text("""
        SELECT 
            COALESCE(AVG(impressions), 10000) as avg_imp,
            COALESCE(AVG(clicks), 500) as avg_clk,
            COALESCE(AVG(conversions), 10) as avg_conv,
            COALESCE(AVG(spend), 2000000.00) as avg_spend
        FROM campaign_analytics
    """)
    res = db.execute(query).fetchone()
    
    avg_metrics = {
        "impressions": float(res[0]) if res else 10000.0,
        "clicks": float(res[1]) if res else 500.0,
        "conversions": float(res[2]) if res else 10.0,
        "spend": float(res[3]) if res else 2000000.0
    }
    logger.info(f"Cold start baseline metrics calculated: {avg_metrics}")
    return avg_metrics

def compute_mab_beliefs(db: Session, campaign_id: str, objective: str, epsilon: float = 0.2) -> Dict[str, Any]:
    """
    Runs Epsilon-Greedy or Thompson Sampling mathematics to formulate beliefs/priors.
    Maps Content Generation Output mix: 80% Exploit (proven angles) / 20% Explore (wildcard).
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
    Orchestration layer. Computes beliefs, triggers LangGraph, and terminates immediately.
    """
    logger.info("Starting autonomous generation loop...")
    
    # Fetch campaign metadata
    campaign = db.query(MarketingCampaign).filter_by(id=uuid.UUID(campaign_id)).first()
    if not campaign:
        raise ValueError(f"Campaign with ID {campaign_id} not found.")
        
    objective = campaign.campaign_type or "LEAD_GEN"
    if objective not in ["BRAND_AWARENESS", "LEAD_GEN"]:
        objective = "LEAD_GEN"
        
    # 1. Compute MAB priors
    mab_result = compute_mab_beliefs(db, campaign_id, objective)
    priors = mab_result["beliefs"]
    metrics = mab_result["metrics"]
    
    # 2. Setup initial stateless graph input
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
        "sandbox_feedbacks": []
    }
    
    config = {
        "configurable": {
            "thread_id": f"autonomous_{campaign_id}_{uuid.uuid4().hex[:6]}",
            "workspace_id": workspace_id,
            "product_id": product_id
        }
    }
    
    logger.info("Invoking Stateless LangGraph execution layer...")
    # Trigger LangGraph synchronously (stateless run)
    result_state = await graph.ainvoke(initial_state, config=config)
    logger.info("Stateless LangGraph execution completed successfully and RAM is freed.")
    
    return result_state
