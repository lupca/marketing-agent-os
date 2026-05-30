# app.py
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import uuid
import logging
import asyncio
from typing import cast
import chainlit as cl
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import backend modules
from db.connection import SessionLocal, is_mock
from core.models import Workspace, ProductService
from core.parser import extract_text_from_file, chunk_text
from core.storage import upload_file
from core.rag import store_knowledge
from graphs.main_router import graph
from core.decision_logger import log_decision

# Import FastAPI routing requirements
from chainlit.server import app as fastapi_app
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Request
from core.dashboard import get_dashboard_analytics, simulate_scenario

@fastapi_app.middleware("http")
async def custom_dashboard_middleware(request: Request, call_next):
    """
    Highly robust, fail-safe custom dashboard middleware.
    Intercepts dashboard and vault requests at the HTTP layer, bypassing any Chainlit React SPA routing conflicts.
    Also handles non-ASCII characters in paths (e.g. 'Sếp' to 'Sep') to prevent FastAPI 400 Bad Request.
    """
    # Intercept non-ASCII characters in scope path to prevent FastAPI 400 Bad Request
    raw_path = request.scope.get("path", "")
    if "Sếp" in raw_path or "%E1%BA%BF" in raw_path:
        from urllib.parse import unquote, quote
        decoded = unquote(raw_path)
        if "Sếp" in decoded:
            new_path = decoded.replace("Sếp", "Sep")
            request.scope["path"] = new_path
            request.scope["raw_path"] = quote(new_path).encode("ascii")
            logger.info(f"Rewrote non-ASCII path from {raw_path} to {new_path} to prevent 400 Bad Request")
            
    path = request.url.path
    
    if path == "/" and request.method == "GET":
        # Intercept main page load to set thread_id and short-lived reload cookies
        response = await call_next(request)
        cookies = request.cookies
        thread_id = cookies.get("chat_thread_id")
        if not thread_id:
            thread_id = str(uuid.uuid4())
            response.set_cookie(key="chat_thread_id", value=thread_id, max_age=3600*24*30) # 30 days
        # Set a short-lived cookie indicating the page was reloaded (F5)
        response.set_cookie(key="chat_page_reloaded", value="1", max_age=10)
        return response

    elif path == "/dashboard" and request.method == "GET":
        template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "templates", "dashboard.html"))
        if not os.path.exists(template_path):
            return HTMLResponse(content="<h1>CMO BI Dashboard Template Not Found</h1><p>Please ensure data/templates/dashboard.html exists.</p>", status_code=404)
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
        
    elif (path == "/vault" or path == "/Vault") and request.method == "GET":
        template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "templates", "vault.html"))
        if not os.path.exists(template_path):
            return HTMLResponse(content="<h1>Approved Asset Vault Template Not Found</h1><p>Please ensure data/templates/vault.html exists.</p>", status_code=404)
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)

    elif path == "/api/vault/contents" and request.method == "GET":
        db: Session = SessionLocal()
        try:
            from core.models import MasterContent, PlatformVariant, MarketingCampaign
            approved_contents = db.query(MasterContent).filter(
                MasterContent.approval_status == 'approved'
            ).order_by(MasterContent.created_at.desc()).all()
            
            data = []
            for mc in approved_contents:
                camp = db.query(MarketingCampaign).filter_by(id=mc.campaign_id).first()
                pvs = db.query(PlatformVariant).filter_by(master_content_id=mc.id).all()
                
                variants_list = []
                for pv in pvs:
                    variants_list.append({
                        "platform": pv.platform,
                        "adapted_copy": pv.adapted_copy,
                        "publish_status": pv.publish_status,
                        "created_at": pv.created_at.strftime('%Y-%m-%d %H:%M:%S') if pv.created_at else None
                    })
                
                data.append({
                    "id": str(mc.id),
                    "campaign_name": camp.name if camp else "Chiến dịch tự trị",
                    "core_message": mc.core_message,
                    "created_at": mc.created_at.strftime('%d/%m/%Y %H:%M') if mc.created_at else None,
                    "variants": variants_list
                })
            return JSONResponse(content={"status": "success", "data": data})
        except Exception as e:
            logger.error(f"Error fetching vault contents: {e}", exc_info=True)
            return JSONResponse(content={"error": str(e)}, status_code=500)
        finally:
            db.close()
        
    elif path == "/api/dashboard/metrics" and request.method == "GET":
        db: Session = SessionLocal()
        try:
            data = get_dashboard_analytics(db)
            return JSONResponse(content=data)
        except Exception as e:
            logger.error(f"Error fetching dashboard metrics: {e}", exc_info=True)
            return JSONResponse(content={"error": str(e)}, status_code=500)
        finally:
            db.close()
            
    elif path == "/api/dashboard/simulate" and request.method == "POST":
        db: Session = SessionLocal()
        try:
            body = await request.json()
            test_budget = float(body.get("test_budget", 0))
            price = float(body.get("price", 0))
            cost = float(body.get("cost", 0))
            res = simulate_scenario(test_budget, price, cost, db)
            return JSONResponse(content=res)
        except Exception as e:
            logger.error(f"Error simulating scenario: {e}", exc_info=True)
            return JSONResponse(content={"error": str(e)}, status_code=500)
        finally:
            db.close()
            
    return await call_next(request)

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
    """Initialize session data and database context, recovering previous chat thread if exists."""
    db = SessionLocal()
    thread_id = None
    
    # Read cookies from WebSocket client headers
    client_headers = cl.context.session.client_headers if hasattr(cl.context.session, "client_headers") else {}
    cookie_str = client_headers.get("cookie", "")
    
    cookies = {}
    if cookie_str:
        for item in cookie_str.split(";"):
            if "=" in item:
                k, v = item.strip().split("=", 1)
                cookies[k] = v
                
    cookie_thread_id = cookies.get("chat_thread_id")
    page_reloaded = cookies.get("chat_page_reloaded") == "1"
    
    try:
        # ONLY recover thread on F5 reload (page_reloaded is True)
        if page_reloaded and cookie_thread_id:
            checkpoint_exists = db.execute(text("SELECT 1 FROM checkpoints WHERE thread_id = :tid LIMIT 1"), {"tid": cookie_thread_id}).fetchone()
            if checkpoint_exists:
                thread_id = cookie_thread_id
                logger.info(f"F5 Refresh detected. Recovered active thread_id from cookie: {thread_id}")
                
        if not thread_id:
            # Fallback if first load or not refreshed
            result = db.execute(text("SELECT thread_id FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 1")).fetchone()
            if result:
                thread_id = result[0]
                logger.info(f"Recovered existing thread_id from database: {thread_id}")
    except Exception as e:
        logger.error(f"Error recovering thread_id from database checkpoints: {e}")
    finally:
        db.close()

    if not thread_id:
        thread_id = str(uuid.uuid4())
        logger.info(f"Generated new thread_id: {thread_id}")

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
        f"- Gõ **`vault`** (không cần dấu gạch chéo `/`) để xem ngay kho bài viết quảng cáo chất lượng cao đã phê duyệt!\n"
        f"- Hoặc kéo thả file tài liệu PDF/TXT vào đây để RAG tự động học tri thức!"
    )
    await cl.Message(content=welcome_msg).send()

    # Load and restore past conversation messages onto the UI so history is persistent
    config = {
        "configurable": {
            "thread_id": thread_id,
            "workspace_id": SEED_WORKSPACE_ID,
            "product_id": SEED_PRODUCT_ID
        }
    }
    try:
        state = await graph.aget_state(config)
        if state and state.values and "messages" in state.values:
            past_messages = state.values["messages"]
            logger.info(f"Restoring {len(past_messages)} past messages onto Chainlit UI for thread {thread_id}")
            for msg in past_messages:
                author_name = "Sep (User)" if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and msg.type == "human") else "Marketing OS Agent"
                await cl.Message(content=msg.content, author=author_name).send()
                
            # NEW: Restore active approval actions if the recovered thread is waiting for human approval
            if state.next and state.next[0] == "waiting_approval_barrier":
                logger.info("Restoring active approval cards onto UI for thread...")
                var = state.values.get("variants", [{}])[0]
                cpa = state.values.get("target_cpa", 0.0)
                
                approval_card = (
                    f"### 📥 KỊCH BẢN CHỜ PHÊ DUYỆT (HỒI PHỤC SAU F5)\n"
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
    except Exception as e:
        logger.error(f"Error restoring past conversation onto UI: {e}")

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

    # 2. Intercept /vault command (handling both /vault and vault cleanly to avoid React router redirect)
    cmd = message.content.strip().lower()
    if cmd in ["/vault", "vault", "/vault", "vault"]:
        db = SessionLocal()
        try:
            from core.models import MasterContent, PlatformVariant, MarketingCampaign
            approved_contents = db.query(MasterContent).filter(
                MasterContent.approval_status == 'approved'
            ).order_by(MasterContent.created_at.desc()).all()
            
            if not approved_contents:
                await cl.Message(content="### 🏛️ KHO TÀI SẢN PHÊ DUYỆT (APPROVED ASSET VAULT)\nHiện chưa có kịch bản quảng cáo nào được duyệt. Hãy bắt đầu lên chiến dịch mới và phê duyệt bản nháp để đưa vào kho tài sản nhé!").send()
                return
                
            vault_msg = "## 🏛️ KHO TÀI SẢN PHÊ DUYỆT (APPROVED ASSET VAULT)\nHiển thị danh sách các bài viết quảng cáo chất lượng cao đã qua kiểm duyệt kỹ lưỡng và sẵn sàng mang đi sản xuất:\n\n"
            
            for idx, mc in enumerate(approved_contents):
                camp = db.query(MarketingCampaign).filter_by(id=mc.campaign_id).first()
                camp_name = camp.name if camp else "Chiến dịch tự trị"
                pvs = db.query(PlatformVariant).filter_by(master_content_id=mc.id).all()
                
                vault_msg += f"### 📦 TÀI SẢN {idx+1}: {camp_name}\n"
                vault_msg += f"- **Thông điệp cốt lõi (Core Message):** *\"{mc.core_message}\"* \n"
                vault_msg += f"- **Thời gian duyệt:** `{mc.created_at.strftime('%d/%m/%Y %H:%M')}` \n"
                
                if pvs:
                    vault_msg += "**Kịch bản thích ứng phân phối:**\n"
                    for pv in pvs:
                        vault_msg += f"  *   **Kênh {pv.platform.upper()}:**\n"
                        vault_msg += f"```text\n{pv.adapted_copy}\n```\n"
                vault_msg += "---\n\n"
                
            await cl.Message(content=vault_msg).send()
        except Exception as e:
            logger.error(f"Error querying Approved Vault: {e}", exc_info=True)
            await cl.Message(content=f"❌ Không thể truy vấn Kho tài sản: {str(e)}").send()
        finally:
            db.close()
        return

    # 3. Process text command via LangGraph
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
    
    # NEW: Check if the graph is currently waiting for approval at approval barrier!
    current_state = await graph.aget_state(config)
    if current_state and current_state.next and current_state.next[0] == "waiting_approval_barrier":
        # If they typed a message, treat it exactly as CMO reject feedback!
        logger.info("Human typed chat message while graph paused at approval barrier. Intercepting as edit feedback.")
        feedback_text = message.content.strip()
        await cl.Message(content=f"✍️ **Ghi nhận ý kiến phản hồi của Sếp:** *\"{feedback_text}\"*... Đang chuyển lại Copywriter viết lại bản thảo mới.").send()
        
        state_values = current_state.values if current_state else {}
        variants = state_values.get("variants", [])
        old_copy = variants[0].get("adapted_copy", "") if variants else "Không rõ kịch bản cũ"
        campaign_id = state_values.get("campaign_id")
        
        # Vectorize feedback into RAG
        feedback_content = (
            f"KỊCH BẢN THẤT BẠI TRƯỚC ĐÂY:\n"
            f"- Nội dung cũ: \"{old_copy}\"\n"
            f"- Lý do bị CMO từ chối (Feedback): \"{feedback_text}\"\n"
            f"Yêu cầu: Không được phép sử dụng lại các từ ngữ, cách tiếp cận, hoặc văn phong này!"
        )
        
        db = SessionLocal()
        try:
            store_knowledge(
                db=db,
                workspace_id=uuid.UUID(workspace_id),
                category="manager_feedback",
                source_name=f"cmo_feedback_{uuid.uuid4().hex[:6]}.txt",
                content=feedback_content,
                metadata={
                    "failed_cpa": state_values.get("target_cpa", 0.0),
                    "cmo_feedback": feedback_text,
                    "old_script": old_copy
                }
            )
        except Exception as ve:
            logger.error(f"Failed to vectorize feedback: {ve}")
        finally:
            db.close()
            
        # Log reject decision
        log_decision(
            workspace_id=workspace_id,
            campaign_id=campaign_id,
            agent_name="CMO / CEO",
            action="Reject Script via Chat",
            decision_status="rejected",
            reason=f"CMO đã gõ phản hồi từ chối bản thảo kịch bản nháp. Yêu cầu sửa đổi: \"{feedback_text}\"",
            metadata={"feedback": feedback_text}
        )
        
        # Resume the graph by injecting human feedback and routing back to copywriter
        state_update = {
            "messages": [HumanMessage(content=f"CEO Feedback: {feedback_text}")],
            "sop_stage": "creative_generation"
        }
        await graph.aupdate_state(config, state_update)
        
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
        current_state = await graph.aget_state(config)
        if current_state and current_state.next and current_state.next[0] == "waiting_approval_barrier":
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
        return

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
                
            elif node_name == "researcher_agent":
                new_msgs = node_update.get("messages", [])
                if new_msgs:
                    report = new_msgs[-1].content
                    research_msg = (
                        f"🎯 **[Ban Nghiên Cứu - Researcher]**\n\n"
                        f"{report}"
                    )
                    await cl.Message(content=research_msg).send()

    # 4. Detect if graph is paused or finished
    current_state = await graph.aget_state(config)
    
    # Handle casual chat (END state) gracefully on UI
    if not current_state or not current_state.next:
        # Check if this was a research query which was already handled
        intent = current_state.values.get("intent_classification") if current_state and current_state.values else "chat"
        if intent == "research":
            return
            
        # If the graph has finished (e.g., small talk categorized as END / 'chat')
        # We query the LLM directly or show a standard friendly message
        from core.ollama_client import generate_text
        prompt = (
            f"Bạn là trợ lý Marketing Agent OS. Hãy trả lời thân thiện bằng Tiếng Việt câu hỏi này của Sếp:\n"
            f"\"{message.content}\"\n"
        )
        try:
            logger.info("Generating casual chat response via Ollama...")
            response_text = generate_text(prompt, system_prompt="Trả lời ngắn gọn, vui vẻ, lịch sự và chuyên nghiệp.")
        except Exception:
            response_text = "Dạ, em nghe đây ạ! Em là hệ điều hành Marketing Agent OS. Sếp cần em giúp gì hôm nay ạ? 💻"
            
        await cl.Message(content=response_text).send()

        # Save casual chat reply to graph state checkpoint so it is persistent
        if current_state:
            try:
                await graph.aupdate_state(config, {"messages": [AIMessage(content=response_text)]})
                logger.info("Successfully persisted casual chat response into Postgres checkpointer.")
            except Exception as se:
                logger.error(f"Failed to persist casual chat in checkpointer: {se}", exc_info=True)
        return

    # 5. Detect if graph is paused at Approval Barrier (waiting_approval_barrier)
    current_state = await graph.aget_state(config)
    if current_state and current_state.next and current_state.next[0] == "waiting_approval_barrier":
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
                
    # Fetch final state values to generate and export report
    current_state = await graph.aget_state(config)
    state_values = current_state.values if current_state else {}
    campaign_id = state_values.get("campaign_id") or "auto"
    
    # Log CMO approve decision in agent_decisions table
    log_decision(
        workspace_id=workspace_id,
        campaign_id=campaign_id,
        agent_name="CMO / CEO",
        action="Approve Script",
        decision_status="approved",
        reason="CMO đã kiểm duyệt và phê duyệt bản thảo kịch bản xuất sắc đạt chuẩn (>80đ), kích hoạt tiến trình lên lịch đăng bài tự động.",
        metadata={"thread_id": thread_id}
    )

    # Save UI status message into Graph state messages list
    try:
        pub_status_msg = "🚀 **Chiến dịch đã được kích hoạt thành công!** Đã ghi nhận lịch đăng bài `scheduled` trong database."
        await graph.aupdate_state(config, {"messages": [AIMessage(content=pub_status_msg)]})
    except Exception as e:
        logger.error(f"Error appending publisher UI message to state: {e}")
    
    # Export Marketing Plan report as Markdown document
    try:
        from core.reporter import generate_marketing_plan_markdown
        report_content = generate_marketing_plan_markdown(state_values)
        report_filename = f"marketing_plan_{campaign_id[:8] if campaign_id != 'auto' else 'draft'}.md"
        report_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "reports"))
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, report_filename)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
            
        await cl.Message(content="📂 **Hệ thống đã tự động xuất báo cáo Marketing Plan chi tiết!** Sếp có thể tải xuống chỉ với 1 click:").send()
        
        # Send cl.File to user
        await cl.File(
            path=report_path,
            name=report_filename,
            display="inline"
        ).send()
    except Exception as re:
        logger.error(f"Failed to generate report export: {re}", exc_info=True)
        
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
        
        # 1. Fetch current draft from Graph state values
        current_state = await graph.aget_state(config)
        state_values = current_state.values if current_state else {}
        variants = state_values.get("variants", [])
        old_copy = variants[0].get("adapted_copy", "") if variants else "Không rõ kịch bản cũ"
        campaign_id = state_values.get("campaign_id")
        
        # 2. Vectorize the negative feedback into RAG under category 'manager_feedback'
        feedback_content = (
            f"KỊCH BẢN THẤT BẠI TRƯỚC ĐÂY (variant_id: {variants[0].get('variant_id', 'unknown') if variants else 'unknown'}):\n"
            f"- Nội dung cũ: \"{old_copy}\"\n"
            f"- Lý do bị CMO từ chối (Feedback): \"{feedback_text}\"\n"
            f"Yêu cầu: Không được phép sử dụng lại các từ ngữ, cách tiếp cận, hoặc văn phong này!"
        )
        
        db = SessionLocal()
        try:
            store_knowledge(
                db=db,
                workspace_id=uuid.UUID(workspace_id),
                category="manager_feedback",
                source_name=f"cmo_feedback_{uuid.uuid4().hex[:6]}.txt",
                content=feedback_content,
                metadata={
                    "failed_cpa": state_values.get("target_cpa", 0.0),
                    "cmo_feedback": feedback_text,
                    "old_script": old_copy
                }
            )
            logger.info("Successfully vectorized CMO feedback into rag_knowledgebase!")
        except Exception as ve:
            logger.error(f"Failed to vectorize CMO feedback: {ve}", exc_info=True)
        finally:
            db.close()
            
        # 3. Log CMO reject decision in agent_decisions table
        log_decision(
            workspace_id=workspace_id,
            campaign_id=campaign_id,
            agent_name="CMO / CEO",
            action="Reject Script",
            decision_status="rejected",
            reason=f"CMO đã xem bản thảo kịch bản nháp và từ chối. Yêu cầu sửa đổi: \"{feedback_text}\"",
            metadata={"feedback": feedback_text, "old_script": old_copy}
        )
        
        # Resume the graph by injecting human feedback and routing back to copywriter
        # We update the state first with human feedback in state values
        state_update = {
            "messages": [HumanMessage(content=f"CEO Feedback: {feedback_text}")],
            "sop_stage": "creative_generation"
        }
        await graph.aupdate_state(config, state_update)
        
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
        current_state = await graph.aget_state(config)
        if current_state and current_state.next and current_state.next[0] == "waiting_approval_barrier":
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
