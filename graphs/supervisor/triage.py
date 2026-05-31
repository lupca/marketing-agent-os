# graphs/triage.py
"""
Intelligent Supervisor Hub — 4-Layer Triage Architecture (v3.0)

Kiến trúc:
  Layer 1: Context Aggregator      — Gom 10 tin nhắn gần nhất + trạng thái SOP
  Layer 2: Dynamic Few-Shot        — pgvector tìm 3 mẫu câu tương tự làm gợi ý LLM
  Layer 3: LLM Router (CoT)        — Qwen2.5 suy luận Chain-of-Thought → Structured JSON
  Layer 4: State Injector          — Validate Pydantic → cập nhật AgencyState → dispatch

Thay thế: Vector-Only Router (cosine distance trực tiếp → routing) từ v2.1
"""
import logging
from langchain_core.messages import HumanMessage, AIMessage
from core.dependencies import get_session
from core.models import IntentRoutingKnowledge
from core.ollama_client import get_embedding, generate_text
from core.utils import parse_llm_json, load_prompt
from core.decision_logger import log_decision
from graphs.supervisor.state import AgencyState
from graphs.supervisor.routing_models import RoutingDecision
from config.settings import (
    TRIAGE_CONTEXT_MESSAGES,
    TRIAGE_FEW_SHOT_COUNT,
    TRIAGE_FALLBACK_INTENT
)

logger = logging.getLogger("graphs_triage")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# TRIAGE SYSTEM PROMPT — Layer 3: LLM Router
# ---------------------------------------------------------------------------

# Prompt is loaded dynamically from prompts/supervisor/triage_system.txt


# ---------------------------------------------------------------------------
# LAYER 1: Context Aggregator
# ---------------------------------------------------------------------------

def _aggregate_context(state: AgencyState) -> dict:
    """
    Layer 1 — Thu thập và chuẩn hóa ngữ cảnh hội thoại.
    Lấy TRIAGE_CONTEXT_MESSAGES tin nhắn gần nhất + trạng thái SOP hiện tại.
    """
    messages = state.get("messages", [])
    recent_messages = messages[-TRIAGE_CONTEXT_MESSAGES:]

    context_lines = []
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            role = "👤 User"
        elif isinstance(msg, AIMessage):
            role = "🤖 Agent"
        else:
            role = "System"
        # Truncate dài quá để tránh token bloat
        content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
        context_lines.append(f"[{role}]: {content}")

    return {
        "conversation_history": "\n".join(context_lines) if context_lines else "(Không có lịch sử hội thoại)",
        "message_count": len(recent_messages),
        "current_query": messages[-1].content.strip() if messages else "",
        "active_sop_stage": state.get("sop_stage", "triage"),
        "has_active_campaign": bool(state.get("campaign_id"))
    }


# ---------------------------------------------------------------------------
# LAYER 2: Dynamic Few-Shot Retrieval
# ---------------------------------------------------------------------------

def _retrieve_few_shot_examples(query: str, top_k: int = TRIAGE_FEW_SHOT_COUNT) -> str:
    """
    Layer 2 — Dynamic Few-Shot Retrieval via pgvector.
    Dùng vector similarity để tìm top_k mẫu câu tương tự nhất làm gợi ý cho LLM.
    Không ra quyết định trực tiếp — chỉ cung cấp examples để LLM tự suy luận.
    """
    with get_session() as db:
        try:
            query_vector = get_embedding(query)
            distance_expr = IntentRoutingKnowledge.embedding.cosine_distance(query_vector)

            results = (
                db.query(IntentRoutingKnowledge, distance_expr)
                .filter(IntentRoutingKnowledge.is_active == True)
                .order_by(distance_expr)
                .limit(top_k)
                .all()
            )

            if not results:
                logger.warning("Layer 2: Không tìm thấy mẫu few-shot nào trong DB.")
                return "(Không có mẫu tham khảo trong cơ sở tri thức)"

            examples = []
            for record, distance in results:
                similarity_pct = round((1 - distance) * 100, 1)
                examples.append(
                    f'  • Câu: "{record.utterance}"\n'
                    f'    → Intent: "{record.intent_category}" (tương đồng: {similarity_pct}%)'
                )

            logger.info(f"Layer 2: Tìm thấy {len(examples)} few-shot examples cho query: '{query[:60]}...'")
            return "\n".join(examples)

        except Exception as e:
            logger.error(f"Layer 2 Few-Shot Retrieval Error: {e}")
            return "(Lỗi truy vấn cơ sở tri thức — bỏ qua few-shot)"
# ---------------------------------------------------------------------------
# LAYER 3: LLM Router (Chain-of-Thought + Structured JSON)
# ---------------------------------------------------------------------------

def _run_llm_router(context: dict, few_shot_examples: str, workspace_id: str = None) -> RoutingDecision:
    """
    Layer 3 — LLM Router với Chain-of-Thought.
    Điền ngữ cảnh + few-shot vào System Prompt → gọi Qwen2.5 → parse RoutingDecision.
    """
    triage_prompt_template = load_prompt("supervisor", "triage_system.txt")
    prompt = triage_prompt_template.format(
        few_shot_examples=few_shot_examples,
        sop_stage=context["active_sop_stage"],
        has_active_campaign=context["has_active_campaign"],
        conversation_history=context["conversation_history"],
        message_count=context["message_count"],
        current_query=context["current_query"]
    )

    try:
        raw_response = generate_text(prompt=context["current_query"], system_prompt=prompt, json_format=True, workspace_id=workspace_id)
        logger.info(f"Layer 3 LLM Raw Response: {raw_response[:200]}...")

        parsed_dict = parse_llm_json(raw_response)

        # Validate bằng Pydantic — nếu lỗi field nào sẽ raise ValidationError
        decision = RoutingDecision(**parsed_dict)
        logger.info(
            f"Layer 3 Routing Decision: intent='{decision.intent}', "
            f"is_follow_up={decision.is_follow_up}, "
            f"entities={decision.extracted_entities}"
        )
        return decision

    except Exception as e:
        logger.error(f"Layer 3 LLM Router Error: {e}.")
        raise ValueError("Dữ liệu AI trả về không hợp lệ, không thể tiếp tục") from e


# ---------------------------------------------------------------------------
# LAYER 4: State Injector & Dispatcher (triage_node entry point)
# ---------------------------------------------------------------------------

def triage_node(state: AgencyState) -> dict:
    """
    Intelligent Supervisor Hub — Entry Gateway của toàn bộ hệ thống.

    4-Layer Pipeline:
      L1: Context Aggregator  → gom 10 tin nhắn gần nhất + sop_stage
      L2: Few-Shot Retrieval  → pgvector tìm 3 mẫu câu gợi ý cho LLM
      L3: LLM Router (CoT)   → Qwen2.5 suy luận → RoutingDecision JSON
      L4: State Injector      → validate Pydantic → cập nhật AgencyState

    Returns: dict cập nhật AgencyState với intent, is_follow_up, extracted_entities, thought_process.
    """
    logger.info("=" * 60)
    logger.info("Executing Intelligent Supervisor Hub (4-Layer Triage)...")

    # Guard: không có messages
    messages = state.get("messages", [])
    if not messages:
        logger.warning("Triage: Không có messages trong state. Fallback về research.")
        return {
            "sop_stage": "triage",
            "intent_classification": TRIAGE_FALLBACK_INTENT,
            "is_follow_up": False,
            "extracted_entities": {},
            "routing_thought_process": "Không có tin nhắn đầu vào.",
            "current_channel": "#phong-sang-tao"
        }

    # --- Layer 1: Context Aggregator ---
    logger.info("Layer 1: Aggregating context...")
    context = _aggregate_context(state)
    logger.info(
        f"Layer 1 Done: {context['message_count']} messages aggregated. "
        f"SOP='{context['active_sop_stage']}', "
        f"ActiveCampaign={context['has_active_campaign']}"
    )

    # --- Layer 2: Dynamic Few-Shot Retrieval ---
    logger.info("Layer 2: Retrieving few-shot examples from pgvector...")
    few_shot_examples = _retrieve_few_shot_examples(context["current_query"])

    # Workspace ID for multi-tenant isolation
    ws_id = state.get("workspace_id")

    # Load unified business context (DNA) once
    business_context = state.get("business_context")
    if not business_context:
        from core.db_services import get_unified_business_context
        import uuid
        product_id = state.get("product_id")
        p_uuid = None
        if product_id:
            try:
                p_uuid = uuid.UUID(str(product_id))
            except Exception:
                pass
        try:
            ws_uuid = uuid.UUID(str(ws_id))
            business_context = get_unified_business_context(ws_uuid, p_uuid)
        except Exception as e:
            logger.error(f"Error fetching unified business context in Triage: {e}")
            business_context = {}

    # --- Layer 3: LLM Router ---
    logger.info("Layer 3: Running LLM Router (Chain-of-Thought)...")
    decision = _run_llm_router(context, few_shot_examples, workspace_id=ws_id)

    # --- Layer 4: State Injector ---
    logger.info("Layer 4: Injecting routing decision into AgencyState...")

    # Xác định kênh Chainlit dựa trên intent
    channel_map = {
        "create_campaign": "#phong-kinh-doanh",
        "show_metrics": "#phong-kinh-doanh",
        "research": "#phong-sang-tao",
        "chat": "#phong-sang-tao",
        "creative_report": "#phong-sang-tao"
    }
    channel = channel_map.get(decision.intent, "#phong-sang-tao")

    # Log quyết định vào AgentDecision table (Observability)

    log_decision(
        workspace_id=ws_id,
        agent_name="Intelligent Supervisor Hub",
        action="Route Intent (4-Layer)",
        decision_status="success",
        reason=(
            f"Intent='{decision.intent}' | "
            f"is_follow_up={decision.is_follow_up} | "
            f"Kênh={channel}"
        ),
        metadata={
            "intent": decision.intent,
            "is_follow_up": decision.is_follow_up,
            "extracted_entities": decision.extracted_entities,
            "thought_process": decision.thought_process,
            "query": context["current_query"]
        }
    )

    logger.info(
        f"Triage Complete: '{context['current_query'][:60]}' "
        f"→ intent='{decision.intent}', channel='{channel}'"
    )
    logger.info("=" * 60)

    return {
        "sop_stage": "triage",
        "intent_classification": decision.intent,
        "is_follow_up": decision.is_follow_up,
        "extracted_entities": decision.extracted_entities,
        "routing_thought_process": decision.thought_process,
        "current_channel": channel,
        "business_context": business_context
    }


# ---------------------------------------------------------------------------
# Conditional Router — route_after_triage (không đổi interface)
# ---------------------------------------------------------------------------

def route_after_triage(state: AgencyState) -> str:
    """
    Conditional Edge Function: Đọc intent từ state và chọn node tiếp theo.
    Interface giữ nguyên để main_router.py không cần thay đổi cấu trúc graph.
    """
    intent = state.get("intent_classification", TRIAGE_FALLBACK_INTENT)
    logger.info(f"Conditional Router → intent='{intent}'")

    routing_table = {
        "create_campaign": "analyst",
        "show_metrics": "performance",
        "research": "researcher_agent",
        "chat": "chat_agent",
        "creative_report": "creative_report_agent"
    }

    next_node = routing_table.get(intent, "researcher_agent")
    logger.info(f"Dispatching to node: '{next_node}'")
    return next_node
