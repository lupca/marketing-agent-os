# scratch/test_dry_run.py
import os
import sys
import uuid

# Add root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 1. Define Mock LLM response generator
def mock_generate_text(prompt, system_prompt=None, json_format=False):
    print(f"\n--- MOCK LLM CALLED ---")
    print(f"System Prompt: {system_prompt}")
    print(f"Prompt length: {len(prompt)}")
    print(f"JSON Format requested: {json_format}")
    
    # Reranker prompt
    if "Rate the relevance" in prompt:
        print(" -> Returning mock rerank score: 0.95")
        return "0.95"
        
    # Strategist prompt
    if "ANGLE_STRATEGIST" in prompt or ("G-Agent Tech" in prompt and "Consideration" in prompt):
        print(" -> Returning mock strategist angle")
        return """
        {
            "angle_name": "Góc giải phóng thời gian (Mock Angle)",
            "funnel_stage": "Consideration",
            "psychological_angle": "Logic",
            "pain_point_focus": "CMO không có thời gian duyệt từng kịch bản quảng cáo",
            "key_message_variation": "Để AI Agent tự viết kịch bản, chấm điểm và báo cáo, giải phóng 80% thời gian điều hành Ads của bạn.",
            "call_to_action_direction": "Đăng ký dùng thử bản Demo Agent OS ngay",
            "brief": "Mở đầu: Cảnh báo việc đốt thời gian của sếp. Thân bài: Cơ chế Guardian chấm điểm tự động. Kết bài: Đăng ký demo."
        }
        """
        
    # Copywriter Master Content prompt
    if "MASTER_CONTENT" in prompt or "MASTER_CONTENT_GENERATOR_PROMPT" in prompt or "master content" in prompt or "Tối ưu chi phí" in prompt:
        print(" -> Returning mock copywriter master content")
        return """
        {
            "core_message": "Marketing Agent OS v2.0 - Để AI tự viết kịch bản, chấm điểm và tự động tắt ads lỗ, giữ CPA ổn định!",
            "extended_message": "Nếu bạn là một CMO bận rộn đang đau đầu vì chi phí ads tăng vọt và mất thời gian duyệt bài viết, giải pháp Multi-agent tự trị LangGraph chính là cứu cánh của bạn. Hệ thống tự động tính CPA Target, gò Copywriter viết đúng hướng, và Performance Node tự tắt ads lỗ. Hãy giải phóng 80% thời gian của bạn ngay hôm nay.",
            "tone_markers": ["Chuyên nghiệp", "Sắc bén", "Hiệu suất"],
            "suggested_hashtags": ["#CPAAds", "#AgentOS", "#LangGraph"],
            "call_to_action": "Đăng ký dùng thử bản demo ngay",
            "key_benefits": ["Tiết kiệm 80% thời gian", "CPA an toàn dưới Target", "Scoring 100đ nghiêm ngặt"],
            "confidence_score": 4.5,
            "video_hook_idea": "Sếp đang ngồi đau đầu vì báo cáo ads đỏ lòm, đột nhiên AI báo cáo đã tự động tắt 3 chiến dịch lỗ.",
            "video_setting_suggestion": "Văn phòng làm việc buổi tối muộn"
        }
        """
        
    # Copywriter Facebook variant prompt
    if "PLATFORM_VARIANT" in prompt or "facebook" in prompt:
        print(" -> Returning mock facebook platform variant")
        return """
        {
            "adapted_copy": "SẾP CÓ ĐANG ĐỐT TIỀN CHO ADS? 💸\\n\\nLà một CMO, bạn mất bao nhiêu giờ mỗi tuần để duyệt kịch bản quảng cáo và canh tắt ads lỗ?\\n\\nVới Marketing Agent OS v2.0, Ban Kinh Doanh tự động tính toán CPA Target và ép Copywriter viết đúng khuôn. Brand Guardian chấm điểm nghiêm ngặt đạt trên 80đ mới cho duyệt.\\n\\n👉 Nhấn đăng ký để nhận ngay bản Demo miễn phí!",
            "seoTitle": "Marketing Agent OS v2.0 - Giải Pháp Tối Ưu CPA Tự Động",
            "seoDescription": "Phần mềm tích hợp LangGraph tự động hóa ads, tự động tắt camp vượt CPA Target.",
            "seoKeywords": ["tự động ads", "giảm CPA", "marketing agent"],
            "hashtags": ["#TựĐộngHóaAds", "#TốiƯuCPA", "#AgentOS"],
            "summary": "Mẫu copy chuyển đổi ads tối ưu cho sếp bận rộn",
            "callToAction": "Đăng ký nhận Demo",
            "platform_tips": "Đăng vào khung giờ hành chính thứ 3 và thứ 5",
            "aiPrompt_used": "Facebook platform variant generator",
            "confidence_score": 4.7,
            "character_count": 350,
            "optimization_notes": "Sử dụng emoji tiền và báo động để giật tít nỗi đau."
        }
        """
        
    # Brand Guardian prompt
    if "EDITOR_BRAND_GUARDIAN" in prompt or "Brand Guardian" in prompt or "CMO 100-Point" in prompt:
        print(" -> Returning mock brand guardian evaluation")
        return """
        {
            "score": 85,
            "feedback_reason": "Đạt chỉ tiêu hoàn hảo: Hook tốt, đúng giọng văn thương hiệu chuyên nghiệp."
        }
        """
        
    print(" -> Returning empty JSON")
    return "{}"

# Mock Embedding generator
def mock_get_embedding(text_content):
    return [0.1] * 1024

# Mock triage node
def mock_triage_node(state):
    print("\n--- MOCK TRIAGE CALLED ---")
    print(" -> Routing to create_campaign")
    return {
        "sop_stage": "triage",
        "intent_classification": "create_campaign",
        "current_channel": "#phong-sang-tao"
    }

# 2. Monkeypatch core.ollama_client BEFORE importing other graphs or db components!
import core.ollama_client
core.ollama_client.generate_text = mock_generate_text
core.ollama_client.get_embedding = mock_get_embedding

# 3. Now import graphs, db components
from db.connection import SessionLocal
from db.seed import seed_database
from core.models import PlatformVariant
from graphs.main_router import builder
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver  # Lightweight sync memory checkpointer!

# Overwrite the runnable inside 'triage' StateNodeSpec!
builder.nodes["triage"].runnable = mock_triage_node

# Compile graph with MemorySaver!
graph = builder.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["waiting_approval_barrier"]
)

SEED_WORKSPACE_ID = "00000000-0000-0000-0000-000000000002"
SEED_PRODUCT_ID = "00000000-0000-0000-0000-000000000005"

def run_dry_test():
    print("Initializing test database...")
    db = SessionLocal()
    seed_database(db)
    db.close()
    
    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
            "workspace_id": SEED_WORKSPACE_ID,
            "product_id": SEED_PRODUCT_ID
        }
    }
    
    initial_state = {
        "messages": [HumanMessage(content="Lên camp mới cho sản phẩm G-Agent Tech")],
        "current_channel": "#phong-kinh-doanh",
        "workspace_id": SEED_WORKSPACE_ID,
        "product_id": SEED_PRODUCT_ID,
        "sop_stage": "triage",
        "feedback_log": [],
        "killed_variants_feedback": []
    }
    
    print("\nRunning the LangGraph multi-agent workflow...")
    for event in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node_name, node_update in event.items():
            print(f" -> Completed Node: '{node_name}'")
            if isinstance(node_update, dict):
                print(f"    Update keys: {list(node_update.keys())}")
            else:
                print(f"    Update: {node_update}")
            
    print("\nVerifying approval barrier...")
    current_state = graph.get_state(config)
    print(f"Next active node in LangGraph: {current_state.next}")
    assert current_state.next[0] == "waiting_approval_barrier", "Graph should pause at approval barrier!"
    
    print("\nResuming LangGraph (CEO Approved)...")
    for event in graph.stream(None, config=config, stream_mode="updates"):
        for node_name, node_update in event.items():
            print(f" -> Completed Resumed Node: '{node_name}'")
            if isinstance(node_update, dict):
                print(f"    Update keys: {list(node_update.keys())}")
            else:
                print(f"    Update: {node_update}")
            
    print("\nGraph completed successfully!")

if __name__ == "__main__":
    run_dry_test()
