# app.py
import os
import uuid
import logging
import asyncio
from typing import cast
import chainlit as cl
from langchain_core.messages import HumanMessage, AIMessage
from langchain.schema.runnable.config import RunnableConfig
from sqlalchemy.orm import Session

# Import backend modules
from db.connection import SessionLocal, is_mock
from core.models import Workspace, ProductService
from core.parser import extract_text_from_file, chunk_text
from core.storage import upload_file
from core.rag import store_knowledge
from graphs.main_router import graph

logger = logging.getLogger("chainlit_app")
logging.basicConfig(level=logging.INFO)

# Default workspace and product identifiers (Matching database seeds)
SEED_WORKSPACE_ID = "00000000-0000-0000-0000-000000000002"
SEED_PRODUCT_ID = "00000000-0000-0000-0000-000000000005"

@cl.set_chat_profiles
async def chat_profile():
    """Setup multi-department channels on UI sidebar."""
    return [
        cl.ChatProfile(
            name="#phong-kinh-doanh",
            markdown_description="Nơi CMO giám sát chỉ số Ads, tính CPA Target và duyệt Ngân sách vĩ mô.",
            icon="https://cdn-icons-png.flaticon.com/512/3135/3135706.png"
        ),
        cl.ChatProfile(
            name="#phong-sang-tao",
            markdown_description="Quan sát Ban Sáng Tạo (Strategist, Copywriter, Guardian) thảo luận và viết kịch bản.",
            icon="https://cdn-icons-png.flaticon.com/512/3242/3242257.png"
        )
    ]

@cl.on_chat_start
async def on_chat_start():
    """Initialize session data and database context."""
    thread_id = str(uuid.uuid4())
    cl.user_session.set("thread_id", thread_id)
    cl.user_session.set("workspace_id", SEED_WORKSPACE_ID)
    cl.user_session.set("product_id", SEED_PRODUCT_ID)
    
    # Establish connection status greeting
    profile = cl.user_session.get("chat_profile", "#phong-kinh-doanh")
    db_mode = "MOCK SQLite (Offline)" if is_mock() else "PostgreSQL (Online)"
    
    welcome_msg = (
        f"### 🖥️ Hệ Điều Hành Marketing Agent OS v2.0 Khởi Động!\n"
        f"- **Môi trường CSDL:** `{db_mode}`\n"
        f"- **Thread ID:** `{thread_id}`\n"
        f"- **Kênh đang chọn:** `{profile}`\n\n"
        f"**Sếp cần giao việc gì hôm nay?**\n"
        f"- Để tạo chiến dịch mới, nhập ví dụ: *\"Lên camp mới cho sản phẩm G-Agent Tech\"*\n"
        f"- Để xem báo cáo hiệu suất, nhập ví dụ: *\"Xem báo cáo CPA tuần qua\"*\n"
        f"- Hoặc kéo thả file tài liệu PDF/TXT vào đây để RAG tự động học tri thức!"
    )
    await cl.Message(content=welcome_msg).send()

async def run_vectorization_pipeline(element) -> str:
    """Run S3 upload, parsing, text chunking, and pgvector database storing asynchronously."""
    db: Session = SessionLocal()
    workspace_id = cl.user_session.get("workspace_id")
    
    # Write incoming stream to temp file
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "temp"))
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, element.name)
    
    with open(temp_file_path, "wb") as f:
        f.write(element.content)
        
    try:
        # 1. Upload to MinIO S3
        object_key = f"workspaces/{workspace_id}/knowledge/{element.name}"
        file_url = upload_file(temp_file_path, object_key)
        
        # 2. Extract Text
        text_content = extract_text_from_file(temp_file_path)
        
        # 3. Chunk Text
        chunks = chunk_text(text_content, chunk_size=500, overlap=50)
        
        # 4. Generate Embeddings & Store in pgvector
        stored_count = 0
        for i, chunk in enumerate(chunks):
            metadata = {
                "source_file": element.name,
                "file_url": file_url,
                "chunk_index": i,
                "start_idx": chunk["start_idx"],
                "end_idx": chunk["end_idx"]
            }
            store_knowledge(
                db=db,
                workspace_id=uuid.UUID(workspace_id),
                category="user_upload",
                source_name=element.name,
                content=chunk["content"],
                metadata=metadata
            )
            stored_count += 1
            
        success_msg = (
            f"### ✅ Vector hóa tài liệu thành công!\n"
            f"- **Tên file:** `{element.name}`\n"
            f"- **S3 Storage URL:** [Xem tệp tin]({file_url})\n"
            f"- **Số phân đoạn tri thức đã nạp:** `{stored_count} chunks`\n\n"
            f"Ban Sáng Tạo đã tiếp thu tri thức này và sẵn sàng áp dụng cho các bài viết tiếp theo!"
        )
        db.close()
        return success_msg
        
    except Exception as e:
        logger.error(f"Error vectorizing file: {e}")
        db.close()
        return f"❌ Lỗi xử lý tài liệu '{element.name}': {str(e)}"
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@cl.on_message
async def on_message(message: cl.Message):
    """Handle chat messages, file imports, and orchestrate LangGraph."""
    # 1. Intercept file uploads (SOP Interactive Vectorization)
    if message.elements:
        for element in message.elements:
            if element.type == "file":
                # Show loader
                loader = cl.Message(content=f"⚙️ Đang xử lý tài liệu '{element.name}'...")
                await loader.send()
                
                result = await run_vectorization_pipeline(element)
                
                # Update loader with result
                loader.content = result
                await loader.update()
        return

    # 2. Process text command via LangGraph
    thread_id = cl.user_session.get("thread_id")
    workspace_id = cl.user_session.get("workspace_id")
    product_id = cl.user_session.get("product_id")
    current_channel = cl.user_session.get("chat_profile", "#phong-kinh-doanh")
    
    # Configure graph runner state
    config = {
        "configurable": {
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "product_id": product_id
        }
    }
    
    initial_state = {
        "messages": [HumanMessage(content=message.content)],
        "current_channel": current_channel,
        "workspace_id": workspace_id,
        "product_id": product_id,
        "sop_stage": "triage",
        "feedback_log": [],
        "killed_variants_feedback": []
    }
    
    # Run Compiled LangGraph Asynchronously
    # We step through nodes to stream intermediate thoughts cleanly
    cb = cl.LangchainCallbackHandler()
    logger.info("Triggering LangGraph state stream...")
    
    async for event in graph.astream(initial_state, config=RunnableConfig(callbacks=[cb], **config), stream_mode="updates"):
        # Detect active node execution
        for node_name, node_update in event.items():
            logger.info(f"Node '{node_name}' finished execution.")
            
            # Stream custom logs based on active channels
            if node_name == "triage":
                # Intent analysis feedback
                stage = node_update.get("sop_stage")
                logger.info(f"Triage complete. Stage: {stage}")
                
            elif node_name == "analyst":
                cpa = node_update.get("target_cpa")
                budget = node_update.get("test_budget")
                analyst_msg = (
                    f"🎯 **[Phòng Kinh Doanh - Analyst]**\n"
                    f"- Đã tính toán xong Điểm Neo kinh tế sống còn.\n"
                    f"- **CPA Target:** `{cpa:,.0f} VNĐ` / đơn hàng.\n"
                    f"- **Ngân sách Test tối đa:** `{budget:,.0f} VNĐ`."
                )
                await cl.Message(content=analyst_msg).send()
                
            elif node_name == "performance":
                # Scale / Kill results
                killed = node_update.get("killed_variants_feedback", [])
                if killed:
                    kill_msg = (
                        f"🚨 **[Phòng Kinh Doanh - Performance]**\n"
                        f"- Phát hiện `{len(killed)} kịch bản` vượt ngưỡng CPA!\n"
                        f"- variant_id: `{killed[0].get('variant_id')}` bị TẮT (Killed) do CPA đạt `{killed[0].get('failed_cpa'):,.0f} VNĐ` > Target `{target_cpa:,.0f} VNĐ`.\n"
                        f"👉 **Giao thức cãi nhau:** Gửi phản hồi nóng bắt Ban Sáng Tạo đổi Angle viết lại!"
                    )
                    await cl.Message(content=kill_msg).send()
                else:
                    await cl.Message(content="📈 **[Phòng Kinh Doanh - Performance]** Không phát hiện Ads vượt ngưỡng CPA. Mọi thứ vận hành an toàn.").send()
                    
            elif node_name == "strategist":
                angle = node_update.get("current_angle", {})
                strat_msg = (
                    f"🧠 **[Phòng Sáng Tạo - Strategist]**\n"
                    f"- Đã nghiên cứu RAG và tự động dán RAG bài học thất bại.\n"
                    f"- **Angle đề xuất:** `{angle.get('angle_name')}`\n"
                    f"- **Nỗi đau đánh trúng:** \"{angle.get('pain_point_focus')}\"\n"
                    f"- **Tập trung:** {angle.get('psychological_angle')}"
                )
                # Show tocreative channel if needed, or post directly
                await cl.Message(content=strat_msg).send()
                
            elif node_name == "copywriter":
                # Copy writing completed
                var = node_update.get("variants", [])[0]
                copy_msg = (
                    f"✍️ **[Phòng Sáng Tạo - Copywriter]**\n"
                    f"- Đã xào nấu và tối ưu hóa kịch bản theo target CPA.\n"
                    f"- **Nội dung nháp Facebook:**\n\n"
                    f"```text\n{var.get('adapted_copy')}\n```\n"
                    f"- **Tags:** {', '.join(var.get('hashtags', []))}"
                )
                await cl.Message(content=copy_msg).send()
                
            elif node_name == "guardian":
                # Scoring validation
                logs = node_update.get("feedback_log", [])
                await cl.Message(content=f"🛡️ **[Phòng Sáng Tạo - Brand Guardian]**\n- Kết quả: `{logs[-1]}`").send()

    # 3. Detect if graph is paused at Approval Barrier (waiting_approval_barrier)
    current_state = graph.get_state(config)
    if current_state.next and current_state.next[0] == "waiting_approval_barrier":
        logger.info("Approval barrier detected! Rendering action buttons for CEO.")
        
        # Fetch proposed copy from state
        state_values = current_state.values
        var = state_values.get("variants", [{}])[0]
        cpa = state_values.get("target_cpa", 0.0)
        
        approval_card = (
            f"### 📥 KỊCH BẢN CHỜ PHÊ DUYỆT (HUMAN-IN-THE-LOOP)\n"
            f"- **Kênh đề xuất:** `Facebook Ads`\n"
            f"- **Ngưỡng target CPA tối đa:** `{cpa:,.0f} VNĐ` / đơn.\n\n"
            f"**Kịch bản đề xuất:**\n"
            f"```text\n{var.get('adapted_copy')}\n```\n"
            f"Sếp xem và duyệt chiến dịch vĩ mô này:"
        )
        
        actions = [
            cl.Action(name="cmo_approve", value="approved", label="Duyệt và Đăng 🚀"),
            cl.Action(name="cmo_reject", value="rejected", label="Yêu cầu sửa ✍️")
        ]
        
        await cl.Message(content=approval_card, actions=actions).send()

@cl.action_callback("cmo_approve")
async def on_approve(action: cl.Action):
    """Resume LangGraph with approval token."""
    thread_id = cl.user_session.get("thread_id")
    workspace_id = cl.user_session.get("workspace_id")
    product_id = cl.user_session.get("product_id")
    
    config = {
        "configurable": {
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "product_id": product_id
        }
    }
    
    await cl.Message(content="✅ **Sếp đã bấm Duyệt!** Đang đồng bộ CSDL và lên lịch đăng bài tự động...").send()
    
    # Resume the graph by passing None to waiting_approval_barrier
    async for event in graph.astream(None, config=config, stream_mode="updates"):
        for node_name, node_update in event.items():
            if node_name == "publisher":
                await cl.Message(content="🚀 **Chiến dịch đã được kích hoạt thành công!** Đã ghi nhận lịch đăng bài `scheduled` trong database.").send()
                
    # Remove action card
    await action.remove()

@cl.action_callback("cmo_reject")
async def on_reject(action: cl.Action):
    """Resume LangGraph with negative feedback."""
    thread_id = cl.user_session.get("thread_id")
    workspace_id = cl.user_session.get("workspace_id")
    product_id = cl.user_session.get("product_id")
    
    config = {
        "configurable": {
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "product_id": product_id
        }
    }
    
    # Ask sếp what to edit
    res = await cl.AskUserMessage(content="Sếp cần chỉnh sửa những gì? Nhập ý kiến phản hồi tại đây:").send()
    if res:
        feedback_text = res["output"]
        await cl.Message(content=f"✍️ Gửi phản hồi sang Copywriter: *\"{feedback_text}\"*... Đang viết lại bản thảo mới.").send()
        
        # Resume the graph by injecting human feedback and routing back to copywriter
        # We update the state first with human feedback in state values
        state_update = {
            "messages": [HumanMessage(content=f"CEO Feedback: {feedback_text}")],
            "sop_stage": "creative_generation"
        }
        graph.update_state(config, state_update)
        
        # Resume graph stream
        cb = cl.LangchainCallbackHandler()
        async for event in graph.astream(None, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                if node_name == "copywriter":
                    var = node_update.get("variants", [])[0]
                    copy_msg = (
                        f"✍️ **[Bản Thảo Viết Lại của Copywriter]**\n"
                        f"```text\n{var.get('adapted_copy')}\n```"
                    )
                    await cl.Message(content=copy_msg).send()
                elif node_name == "guardian":
                    logs = node_update.get("feedback_log", [])
                    await cl.Message(content=f"🛡️ **[Phòng Sáng Tạo - Brand Guardian]**\n- Kết quả chấm lại: `{logs[-1]}`").send()
                    
        # Check if paused again
        current_state = graph.get_state(config)
        if current_state.next and current_state.next[0] == "waiting_approval_barrier":
            var = current_state.values.get("variants", [{}])[0]
            approval_card = (
                f"### 📥 BẢN THẢO VIẾT LẠI CHỜ DUYỆT\n"
                f"```text\n{var.get('adapted_copy')}\n```"
            )
            new_actions = [
                cl.Action(name="cmo_approve", value="approved", label="Duyệt và Đăng 🚀"),
                cl.Action(name="cmo_reject", value="rejected", label="Yêu cầu sửa tiếp ✍️")
            ]
            await cl.Message(content=approval_card, actions=new_actions).send()

    await action.remove()
