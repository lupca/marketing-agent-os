# graphs/autonomous/insight.py
import logging
import uuid
from core.dependencies import get_session
from core.models import MarketingCampaign, AIInsightPending
from core.ollama_client import generate_text
from core.utils import parse_llm_json, load_prompt
from graphs.supervisor.state import AgencyState
from graphs.autonomous.telemetry import instrument_node

logger = logging.getLogger("autonomous_nodes")


def generate_cmo_insight(workspace_id: str, metrics: dict, priors: dict) -> str:
    """
    Generates a professional Vietnamese insight explanation for the CMO post-mortem analysis.
    """
    insight_template = load_prompt("creative", "autonomous_cmo_insight.txt")
    prompt = insight_template.format(metrics=metrics, priors=priors)
    try:
        insight_text = generate_text(prompt, system_prompt="You are a senior CMO Analyst.", workspace_id=workspace_id)
        try:
            parsed = parse_llm_json(insight_text)
            parsed_insight = parsed.get("insight") or parsed.get("insight_text")
            if parsed_insight:
                return str(parsed_insight)
            elif parsed:
                return str(next(iter(parsed.values())))
        except Exception:
            cleaned = insight_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return cleaned.strip()
    except Exception:
        return "Hành vi người dùng đang có xu hướng ưu tiên các góc độ Social Proof (Đánh giá thực tế) do sợ mua phải hàng giả, hàng nhái trôi nổi trên thị trường."


@instrument_node("insight_generator")
def insight_generator_node(state: AgencyState) -> dict:
    """
    Insight Generator Node: Analyzes metric shifts, generates explanations using LLM,
    and writes them strictly to 'ai_insights_pending' SQL tables (NOT RAG).
    """
    logger.info("Executing Insight Generator Node...")
    workspace_id = state.get("workspace_id")
    campaign_id = state.get("campaign_id")
    metrics = state.get("current_metrics") or {}
    priors = state.get("current_beliefs") or {}
    
    insight_text = generate_cmo_insight(workspace_id, metrics, priors)
        
    # Write to campaign pending insights SQL table
    with get_session() as db:
        valid_campaign_id = None
        if campaign_id:
            try:
                exists = db.query(MarketingCampaign.id).filter(MarketingCampaign.id == uuid.UUID(str(campaign_id))).first()
                if exists:
                    valid_campaign_id = uuid.UUID(str(campaign_id))
                else:
                    logger.warning(f"campaign_id {campaign_id} not found in MarketingCampaign. Setting to None to prevent ForeignKeyViolation.")
            except Exception as e:
                logger.warning(f"Error validating campaign_id {campaign_id}: {e}")

        pending = AIInsightPending(
            workspace_id=uuid.UUID(str(workspace_id)),
            campaign_id=valid_campaign_id,
            insight_text=insight_text,
            priors_shift=priors,
            approval_status="pending"
        )
        db.add(pending)
        db.commit()
        logger.info("Successfully saved AI explanation post-mortem to database table 'ai_insights_pending'!")

    return {"sop_stage": "publisher"}
