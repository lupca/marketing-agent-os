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
from db.connection import  is_mock
from core.dependencies import get_session
from core.models import Workspace, ProductService
from core.parser import extract_text_from_file, semantic_chunk_text
from core.storage import upload_file
from core.rag import store_document, inject_antipatterns_to_prompt
from graphs.main_router import graph
from core.decision_logger import log_decision

# Import FastAPI routing requirements
from chainlit.server import app as fastapi_app
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Request
from core.dashboard import get_dashboard_analytics, simulate_scenario

# Mount Specialized API Routes
from api.rag_routes import rag_router
from api.vault_routes import vault_router
from api.dashboard_routes import dashboard_router
from api.workspace_routes import workspace_router

fastapi_app.include_router(rag_router)
fastapi_app.include_router(vault_router)
fastapi_app.include_router(dashboard_router)
fastapi_app.include_router(workspace_router)

# Prevent Chainlit's catch-all route (/{full_path:path}) from intercepting RAG API routes
# by moving it to the very end of the route list.
catch_all_route = None
for r in fastapi_app.routes:
    if r.path == "/{full_path:path}":
        catch_all_route = r
        break
if catch_all_route:
    fastapi_app.routes.remove(catch_all_route)
    fastapi_app.routes.append(catch_all_route)
    print("Successfully moved Chainlit catch-all route to the end to prevent API interception.")

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
        
    elif (path == "/settings" or path == "/settings/integrations") and request.method == "GET":
        template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "templates", "settings-integrations.html"))
        if not os.path.exists(template_path):
            # Fallback to old settings.html if new template is missing
            template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "templates", "settings.html"))
        if not os.path.exists(template_path):
            return HTMLResponse(content="<h1>Settings Page Template Not Found</h1><p>Please ensure data/templates/settings-integrations.html exists.</p>", status_code=404)
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)

    elif path == "/settings/models" and request.method == "GET":
        template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "templates", "settings-models.html"))
        if not os.path.exists(template_path):
            return HTMLResponse(content="<h1>AI Models Library Template Not Found</h1><p>Please ensure data/templates/settings-models.html exists.</p>", status_code=404)
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

    elif path == "/knowledge-base" and request.method == "GET":
        template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "public", "knowledge-base.html"))
        if not os.path.exists(template_path):
            return HTMLResponse(content="<h1>Knowledge Base UI Not Found</h1><p>Please ensure public/knowledge-base.html exists.</p>", status_code=404)
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)

    return await call_next(request)

logger = logging.getLogger("chainlit_app")
logging.basicConfig(level=logging.INFO)

# Default workspace and product identifiers (Loaded dynamically from database)
def get_db_seeded_ids():
    """
    Query database dynamically on startup or on-demand to fetch seeded Workspace & Product IDs.
    This eliminates all hardcoded static constants!
    """
    from db.connection import SessionLocal
    from core.models import Workspace, ProductService
    import uuid
    try:
        with SessionLocal() as db:
            ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
            if not ws:
                ws = db.query(Workspace).first()
            ws_id = str(ws.id) if ws else "00000000-0000-0000-0000-000000000002"
            
            prod = None
            if ws:
                prod = db.query(ProductService).filter_by(workspace_id=ws.id).first()
            if not prod:
                prod = db.query(ProductService).first()
            prod_id = str(prod.id) if prod else "00000000-0000-0000-0000-000000000005"
            
            return ws_id, prod_id
    except Exception as e:
        logger.error(f"Error loading seeded IDs from database: {e}")
        return "00000000-0000-0000-0000-000000000002", "00000000-0000-0000-0000-000000000005"

SEED_WORKSPACE_ID, SEED_PRODUCT_ID = get_db_seeded_ids()

def get_workspace_config(thread_id, workspace_id, product_id):
    """
    Returns a unified LangGraph config dictionary, dynamically reading
    recursion_limit from the database workspace settings or falling back to 5.
    """
    with get_session() as db:
        rec_limit = 5
        try:
            ws_id = uuid.UUID(str(workspace_id))
            ws = db.query(Workspace).filter_by(id=ws_id).first()
            if ws and ws.settings:
                # Enforce 5 loops maximum as requested by CTO, but allow dashboard setting
                rec_limit = int(ws.settings.get("recursion_limit") or ws.settings.get("max_loops") or 5)
        except Exception as e:
            logger.error(f"Error loading recursion limit from settings: {e}")
        return {
            "configurable": {
                "thread_id": thread_id,
                "workspace_id": workspace_id,
                "product_id": product_id
            },
            "recursion_limit": rec_limit
        }


# ----------------- v3.2 Track Messages & Render Draft Card -----------------

def track_msg_id(msg_id):
    """Tracks a UI message ID for this turn so it can be mapped to the checkpoint on completion."""
    if not msg_id:
        return
    turn_ids = cl.user_session.get("current_turn_msg_ids") or []
    if msg_id not in turn_ids:
        turn_ids.append(msg_id)
        cl.user_session.set("current_turn_msg_ids", turn_ids)
        logger.info(f"Tracked message ID for current turn: {msg_id}")

async def associate_messages_with_current_checkpoint(config):
    """Maps the tracked message IDs from this turn to the current active checkpoint ID."""
    state = await graph.aget_state(config)
    chk_id = state.config["configurable"].get("checkpoint_id")
    if chk_id:
        msg_ids = cl.user_session.get("current_turn_msg_ids") or []
        if msg_ids:
            mappings = cl.user_session.get("checkpoint_ui_mappings") or {}
            existing = mappings.get(chk_id) or []
            mappings[chk_id] = list(set(existing + msg_ids))
            cl.user_session.set("checkpoint_ui_mappings", mappings)
            cl.user_session.set("current_turn_msg_ids", []) # clear turn list
            logger.info(f"Successfully mapped message IDs {msg_ids} to checkpoint {chk_id}")

async def render_draft_card(config, state_values):
    """Renders the HTML Draft Card showing current NegotiationState values and history select dropdown."""
    history_checkpoints = []
    try:
        async for state in graph.aget_state_history(config):
            draft = state.values.get("draft_plan")
            chk_id = state.config["configurable"].get("checkpoint_id")
            if draft and draft.get("test_budget") and state.next and state.next[0] == "waiting_draft_approval" and chk_id:
                created_at = state.metadata.get("created_at") or "Vừa xong"
                if "T" in created_at:
                    time_part = created_at.split("T")[1].split(".")[0][:5]
                    date_part = created_at.split("T")[0][5:]
                    created_at = f"{time_part} ({date_part})"
                
                if not any(cp["checkpoint_id"] == chk_id for cp in history_checkpoints):
                    history_checkpoints.append({
                        "checkpoint_id": chk_id,
                        "timestamp": created_at,
                        "budget": draft.get("test_budget"),
                        "cpa": draft.get("target_cpa")
                    })
    except Exception as he:
        logger.error(f"Error fetching state history: {he}")
        
    draft = state_values.get("draft_plan") or {}
    budget = draft.get("test_budget") or state_values.get("test_budget") or 2000000.0
    cpa = draft.get("target_cpa") or state_values.get("target_cpa") or 150000.0
    notes = draft.get("notes_for_creative") or "(Không có)"

    is_preserved = False
    if len(history_checkpoints) >= 2:
        prev_budget = history_checkpoints[1]["budget"]
        prev_cpa = history_checkpoints[1]["cpa"]
        if abs(budget - prev_budget) < 0.01 and abs(cpa - prev_cpa) < 0.01:
            is_preserved = True

    badge_html = ""
    if is_preserved:
        badge_html = '<span style="font-size: 11px; background: #e8f0fe; color: #1a73e8; padding: 4px 8px; border-radius: 12px; font-weight: bold; border: 1px solid #1a73e8; margin-left: auto; display: inline-flex; align-items: center; gap: 4px;">ℹ️ Giải thích thắc mắc - Số liệu được bảo toàn</span>'

    options_html = '<option value="" disabled selected>Chọn phiên bản để tua ngược...</option>'
    for idx, cp in enumerate(history_checkpoints):
        options_html += f'<option value="{cp["checkpoint_id"]}">Bản nháp v{len(history_checkpoints)-idx} ({cp["timestamp"]} - CPA: {cp["cpa"]:,.0f}đ)</option>'
        
    html_card = f"""
<div class="draft-card" style="border: 2px solid #1a73e8; padding: 16px; border-radius: 12px; background: #f8f9fa; box-shadow: 0 4px 6px rgba(0,0,0,0.05); font-family: sans-serif;">
  <h3 style="margin-top: 0; color: #1a73e8; display: flex; align-items: center; gap: 8px; justify-content: space-between; flex-wrap: wrap;">
    <span style="display: flex; align-items: center; gap: 8px;">📋 BẢN THẢO CHIẾN DỊCH CHỜ DUYỆT</span>
    {badge_html}
  </h3>
  <div style="display: grid; grid-template-columns: 1fr; gap: 10px; margin-bottom: 12px;">
    <div style="background: #ffffff; padding: 8px 12px; border-radius: 6px; border-left: 4px solid #34a853;">
      <span style="font-size: 12px; color: #666; display: block;">💵 Ngân sách chạy thử:</span>
      <strong style="font-size: 16px; color: #202124;">{budget:,.0f} VNĐ</strong>
    </div>
    <div style="background: #ffffff; padding: 8px 12px; border-radius: 6px; border-left: 4px solid #ea4335;">
      <span style="font-size: 12px; color: #666; display: block;">🎯 CPA mục tiêu:</span>
      <strong style="font-size: 16px; color: #202124;">{cpa:,.0f} VNĐ</strong>
    </div>
    <div style="background: #ffffff; padding: 8px 12px; border-radius: 6px; border-left: 4px solid #fbbc05;">
      <span style="font-size: 12px; color: #666; display: block;">📝 Định hướng / Ghi chú đàm phán:</span>
      <span style="font-size: 14px; color: #202124; font-style: italic;">"{notes}"</span>
    </div>
  </div>
  <div style="margin-top: 15px; border-top: 1px dashed #dadce0; padding-top: 12px;">
    <label style="display: block; font-size: 12px; font-weight: bold; color: #5f6368; margin-bottom: 6px; display: flex; align-items: center; gap: 4px;">
      📜 Lịch sử bản nháp ({len(history_checkpoints)} phiên bản):
    </label>
    <select onchange="window.triggerRewind(this.value)" style="padding: 8px 12px; border-radius: 8px; border: 1px solid #dadce0; width: 100%; font-size: 14px; background: #ffffff; color: #3c4043; cursor: pointer; outline: none; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);">
      {options_html}
    </select>
  </div>
</div>
"""
    
    actions = [
        cl.Action(name="approve_draft", payload={"value": "approved"}, label="Duyệt Khởi Chạy 🚀"),
        cl.Action(name="reject_draft", payload={"value": "rejected"}, label="Yêu cầu sửa ✍️")
    ]
    for cp in history_checkpoints:
        actions.append(cl.Action(name="rewind_draft", payload={"value": cp["checkpoint_id"]}, label=f"rewind-{cp['checkpoint_id']}"))
        
    msg = cl.Message(content=html_card, actions=actions)
    sent_msg = await msg.send()
    track_msg_id(sent_msg.id)
    await associate_messages_with_current_checkpoint(config)



@cl.on_chat_start
async def on_chat_start():
    """Initialize session data and database context, recovering previous chat thread if exists."""
    with get_session() as db:
        thread_id = None
    
        # Read cookies from WebSocket client headers
        env = cl.user_session.get("env") or {}
        cookie_str = env.get("cookie", "")
        if not cookie_str and hasattr(cl.context.session, "client_headers"):
            cookie_str = cl.context.session.client_headers.get("cookie", "")
    
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
        if not thread_id:
            thread_id = str(uuid.uuid4())
            logger.info(f"Generated new thread_id: {thread_id}")

        cl.user_session.set("thread_id", thread_id)
        cl.user_session.set("workspace_id", SEED_WORKSPACE_ID)
        cl.user_session.set("product_id", SEED_PRODUCT_ID)
        # Establish connection status greeting
        profile = cl.user_session.get("chat_profile", "#phong-kinh-doanh")
        db_mode = "MOCK SQLite (Offline)" if is_mock() else "PostgreSQL (Online)"

        # Check for active radar alerts from database
        alert_msg_section = ""
        try:
            alerts = db.execute(text(
                "SELECT reason FROM agent_decisions "
                "WHERE agent_name = 'Market Radar Agent' AND decision_status = 'alert' "
                "ORDER BY created_at DESC LIMIT 3"
            )).fetchall()
            if alerts:
                alert_msg_section = "\n\n⚠️ **[CẢNH BÁO RADAR THỊ TRƯỜNG]**\n"
                for alt in alerts:
                    alert_msg_section += f"- {alt.reason}\n"
        except Exception as e:
            logger.error(f"Error querying active radar alerts: {e}")
    
        welcome_msg = (
            f"### 🖥️ Hệ Điều Hành Marketing Agent OS v3.0 Khởi Động!\n"
            f"- **Môi trường CSDL:** `{db_mode}`\n"
            f"- **Thread ID:** `{thread_id}`\n\n"
            f"**Sếp cần giao việc gì hôm nay?**\n"
            f"- Để tạo chiến dịch mới, nhập ví dụ: *\"Lên camp mới cho sản phẩm G-Agent Tech\"*\n"
            f"- Để xem báo cáo hiệu suất, nhập ví dụ: *\"Xem báo cáo CPA tuần qua\"*\n"
            f"- Gõ **`vault`** (không cần dấu gạch chéo `/`) để xem ngay kho bài viết quảng cáo chất lượng cao đã phê duyệt!\n"
            f"- Hoặc kéo thả file tài liệu PDF/TXT vào đây để RAG tự động học tri thức!{alert_msg_section}"
        )
        await cl.Message(content=welcome_msg).send()

        # Load and restore past conversation messages onto the UI so history is persistent
        config = get_workspace_config(thread_id, SEED_WORKSPACE_ID, SEED_PRODUCT_ID)
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
                        cl.Action(name="cmo_approve", payload={"value": "approved"}, label="Duyệt và Đăng 🚀"),
                        cl.Action(name="cmo_reject", payload={"value": "rejected"}, label="Yêu cầu sửa ✍️")
                    ]
                    await cl.Message(content=approval_card, actions=actions).send()
                
                elif state.next and state.next[0] == "waiting_draft_approval":
                    logger.info("Restoring active draft card onto UI for thread...")
                    await render_draft_card(config, state.values)
        except Exception as e:
            logger.error(f"Error restoring past conversation onto UI: {e}")

async def run_vectorization_pipeline(element) -> str:
    """
    Upload file lên MinIO + tạo RAG document record + kick Celery ingestion task.
    Xử lý hoàn toàn async — không block UI.
    """
    from core.document_service import process_and_store_document, DuplicateDocumentError
    with get_session() as db:
        workspace_id = cl.user_session.get("workspace_id")

        # Read file bytes from element.path (Chainlit stores spontaneous uploads on disk)
        # Fallback to element.content for backwards compatibility
        file_bytes = None
        if hasattr(element, 'path') and element.path:
            try:
                with open(element.path, "rb") as src:
                    file_bytes = src.read()
            except Exception as read_err:
                logger.error(f"Failed to read from element.path '{element.path}': {read_err}")
        if file_bytes is None and hasattr(element, 'content') and element.content:
            file_bytes = element.content
        if file_bytes is None:
            db.close()
            return f"❌ Không thể đọc file '{element.name}'. File rỗng hoặc lỗi upload."

        try:
            doc_info = process_and_store_document(
                db=db,
                workspace_id=str(workspace_id),
                file_bytes=file_bytes,
                file_name=element.name,
                access_tags=["marketing", "global"]
            )

            success_msg = (
                f"### ✅ Tài liệu đã được nhận và đang xử lý!\n"
                f"- **Tên file:** `{doc_info['file_name']}`\n"
                f"- **Document ID:** `{doc_info['document_id']}`\n"
                f"- **Tags:** `marketing, global`\n\n"
                f"⚙️ Hệ thống đang băm vector ngầm (Celery). "
                f"Truy cập **[Knowledge Base](/knowledge-base)** để theo dõi trạng thái và quản lý tags!"
            )
            return success_msg

        except DuplicateDocumentError as e:
            return str(e)
        except Exception as e:
            logger.error(f"Error in run_vectorization_pipeline: {e}", exc_info=True)
            return f"❌ Lỗi xử lý tài liệu '{element.name}': {str(e)}"
@cl.on_message
async def on_message(message: cl.Message):
    """Handle chat messages, file imports, and orchestrate LangGraph."""
    # 1. Intercept file uploads (SOP Interactive Vectorization)
    if message.elements:
        for element in message.elements:
            if isinstance(element, cl.File):
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
        with get_session() as db:
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
                    camp_name = camp.name if camp else ""
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
            return

    # 3. Process text command via LangGraph
    thread_id = cl.user_session.get("thread_id")
    workspace_id = cl.user_session.get("workspace_id")
    product_id = cl.user_session.get("product_id")
    current_channel = cl.user_session.get("chat_profile", "#phong-kinh-doanh")
    
    # Configure graph runner state
    config = get_workspace_config(thread_id, workspace_id, product_id)
    
    # NEW: Check if the graph is currently waiting for approval at approval barrier!
    current_state = await graph.aget_state(config)
    if current_state and current_state.next and current_state.next[0] == "waiting_draft_approval":
        # User typed feedback during draft negotiation
        logger.info("Human typed chat message while graph paused at draft approval barrier. Intercepting as negotiation feedback.")
        feedback_text = message.content.strip()
        track_msg_id(message.id)
        
        user_msg = HumanMessage(content=feedback_text, additional_kwargs={"cl_msg_id": message.id})
        state_update = {
            "messages": [user_msg],
            "draft_approved": False
        }
        await graph.aupdate_state(config, state_update)
        
        async for event in graph.astream(None, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                if node_name == "negotiator":
                    new_msgs = node_update.get("messages", [])
                    if new_msgs:
                        ans_msg = new_msgs[-1].content
                        sent_msg = await cl.Message(content=ans_msg).send()
                        track_msg_id(sent_msg.id)
                        
        await associate_messages_with_current_checkpoint(config)
        new_state = await graph.aget_state(config)
        await render_draft_card(config, new_state.values)
        return

    elif current_state and current_state.next and current_state.next[0] == "waiting_approval_barrier":
        # If they typed a message, treat it exactly as CMO reject feedback!
        logger.info("Human typed chat message while graph paused at approval barrier. Intercepting as edit feedback.")
        feedback_text = message.content.strip()
        track_msg_id(message.id)
        sent_msg = await cl.Message(content=f"✍️ **Ghi nhận ý kiến phản hồi của Sếp:** *\"{feedback_text}\"*... Đang chuyển lại Copywriter viết lại bản thảo mới.").send()
        track_msg_id(sent_msg.id)
        
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
        
        with get_session() as db:
            try:
                # Lưu feedback vào RAG dưới dạng document anti-pattern
                import tempfile, json as _json
                tmp_fb = tempfile.mktemp(suffix=".txt")
                with open(tmp_fb, "w", encoding="utf-8") as _f:
                    _f.write(feedback_content)
                fb_key = f"rag/{workspace_id}/feedback_{uuid.uuid4().hex[:8]}.txt"
                upload_file(tmp_fb, fb_key)
                store_document(
                    db=db,
                    workspace_id=workspace_id,
                    file_name=f"cmo_feedback_{uuid.uuid4().hex[:6]}.txt",
                    file_key=fb_key,
                    access_tags=["manager_feedback", "anti_patterns"],
                    file_size_bytes=len(feedback_content.encode()),
                )
            except Exception as ve:
                logger.error(f"Failed to vectorize feedback: {ve}")
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
                        sent = await cl.Message(content=copy_msg).send()
                        track_msg_id(sent.id)
                    elif node_name == "guardian":
                        logs = node_update.get("feedback_log", [])
                        sent = await cl.Message(content=f"🛡️ **[Phòng Sáng Tạo - Brand Guardian]**\n- Kết quả chấm lại: `{logs[-1]}`").send()
                        track_msg_id(sent.id)
                    
            await associate_messages_with_current_checkpoint(config)
            # Check if paused again
            current_state = await graph.aget_state(config)
            if current_state and current_state.next and current_state.next[0] == "waiting_approval_barrier":
                var = current_state.values.get("variants", [{}])[0]
                approval_card = (
                    f"### 📥 BẢN THẢO VIẾT LẠI CHỜ DUYỆT\n"
                    f"```text\n{var.get('adapted_copy')}\n```"
                )
                new_actions = [
                    cl.Action(name="cmo_approve", payload={"value": "approved"}, label="Duyệt và Đăng 🚀"),
                    cl.Action(name="cmo_reject", payload={"value": "rejected"}, label="Yêu cầu sửa tiếp ✍️")
                ]
                sent = await cl.Message(content=approval_card, actions=new_actions).send()
                track_msg_id(sent.id)
                await associate_messages_with_current_checkpoint(config)
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
    track_msg_id(message.id)
    
    # Run Compiled LangGraph Asynchronously
    cb = cl.LangchainCallbackHandler()
    logger.info("Triggering LangGraph state stream...")
    
    async for event in graph.astream(initial_state, config=RunnableConfig(callbacks=[cb], **config), stream_mode="updates"):
        for node_name, node_update in event.items():
            logger.info(f"Node '{node_name}' finished execution.")
            
            if node_name == "triage":
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
                sent = await cl.Message(content=analyst_msg).send()
                track_msg_id(sent.id)
                
            elif node_name == "performance":
                new_msgs = node_update.get("messages", [])
                if new_msgs:
                    report = new_msgs[-1].content
                    sent = await cl.Message(content=report).send()
                    track_msg_id(sent.id)
                else:
                    killed = node_update.get("killed_variants_feedback", [])
                    if killed:
                        t_cpa = killed[0].get("target_cpa", 1050000.0)
                        kill_msg = (
                            f"🚨 **[Phòng Kinh Doanh - Performance]**\n"
                            f"- Phát hiện `{len(killed)} kịch bản` vượt ngưỡng CPA!\n"
                            f"- variant_id: `{killed[0].get('variant_id')}` bị TẮT (Killed) do CPA đạt `{killed[0].get('failed_cpa'):,.0f} VNĐ` > Target `{t_cpa:,.0f} VNĐ`.\n"
                            f"👉 **Giao thức cãi nhau:** Gửi phản hồi nóng bắt Ban Sáng Tạo đổi Angle viết lại!"
                        )
                        sent = await cl.Message(content=kill_msg).send()
                        track_msg_id(sent.id)
                    else:
                        sent = await cl.Message(content="📈 **[Phòng Kinh Doanh - Performance]** Không phát hiện Ads vượt ngưỡng CPA. Mọi thứ vận hành an toàn.").send()
                        track_msg_id(sent.id)
                    
            elif node_name == "strategist":
                angle = node_update.get("current_angle", {})
                strat_msg = (
                    f"🧠 **[Phòng Sáng Tạo - Strategist]**\n"
                    f"- Đã nghiên cứu RAG và tự động dán RAG bài học thất bại.\n"
                    f"- **Angle đề xuất:** `{angle.get('angle_name')}`\n"
                    f"- **Nỗi đau đánh trúng:** \"{angle.get('pain_point_focus')}\"\n"
                    f"- **Tập trung:** {angle.get('psychological_angle')}"
                )
                sent = await cl.Message(content=strat_msg).send()
                track_msg_id(sent.id)
                
            elif node_name == "copywriter":
                var = node_update.get("variants", [])[0]
                copy_msg = (
                    f"✍️ **[Phòng Sáng Tạo - Copywriter]**\n"
                    f"- Đã xào nấu và tối ưu hóa kịch bản theo target CPA.\n"
                    f"- **Nội dung nháp Facebook:**\n\n"
                    f"```text\n{var.get('adapted_copy')}\n```\n"
                    f"- **Tags:** {', '.join(var.get('hashtags', []))}"
                )
                sent = await cl.Message(content=copy_msg).send()
                track_msg_id(sent.id)
                
            elif node_name == "guardian":
                logs = node_update.get("feedback_log", [])
                sent = await cl.Message(content=f"🛡️ **[Phòng Sáng Tạo - Brand Guardian]**\n- Kết quả: `{logs[-1]}`").send()
                track_msg_id(sent.id)
                
            elif node_name == "researcher_agent":
                new_msgs = node_update.get("messages", [])
                if new_msgs:
                    report = new_msgs[-1].content
                    research_msg = (
                        f"🎯 **[Ban Nghiên Cứu - Researcher]**\n\n"
                        f"{report}"
                    )
                    sent = await cl.Message(content=research_msg).send()
                    track_msg_id(sent.id)
 
            elif node_name == "creative_report_agent":
                new_msgs = node_update.get("messages", [])
                if new_msgs:
                    report = new_msgs[-1].content
                    sent = await cl.Message(content=report).send()
                    track_msg_id(sent.id)
 
            elif node_name == "chat_agent":
                new_msgs = node_update.get("messages", [])
                if new_msgs:
                    report = new_msgs[-1].content
                    sent = await cl.Message(content=report).send()
                    track_msg_id(sent.id)
 
    await associate_messages_with_current_checkpoint(config)
    
    # 4. Detect if graph is paused or finished
    current_state = await graph.aget_state(config)
    
    # Handle casual chat (END state) gracefully on UI
    if not current_state or not current_state.next:
        intent = current_state.values.get("intent_classification") if current_state and current_state.values else "chat"

        # [CTO FIX] BỘ LỌC HOÀN CHỈNH:
        # Nếu LangGraph đã xử lý xong bất kỳ nghiệp vụ nào dưới đây, lập tức DỪNG LẠI (Return).
        # Không được phép gọi LLM để "nói nhảm" thêm một câu nữa gây tốn token và double-dipping.
        if intent in ["research", "chat", "creative_report", "show_metrics", "create_campaign"]:
            return

        # Chỉ lọt xuống đây nếu intent hoàn toàn rác/không xác định.
        # Trả về chuỗi tĩnh, TUYỆT ĐỐI KHÔNG import và gọi generate_text ở đây.
        response_text = "Dạ, em nghe đây ạ! Em là hệ điều hành Marketing Agent OS. Sếp cần em giúp gì hôm nay ạ? 💻"

        sent = await cl.Message(content=response_text).send()
        track_msg_id(sent.id)
        await associate_messages_with_current_checkpoint(config)

        if current_state:
            try:
                # Import AIMessage từ langchain_core.messages nếu chưa có
                from langchain_core.messages import AIMessage
                await graph.aupdate_state(config, {"messages": [AIMessage(content=response_text)]})
                logger.info("Successfully persisted static fallback chat response into Postgres checkpointer.")
            except Exception as se:
                logger.error(f"Failed to persist static fallback chat in checkpointer: {se}", exc_info=True)
        return
 
    # 5. Detect if graph is paused at Approval Barriers
    current_state = await graph.aget_state(config)
    if current_state and current_state.next and current_state.next[0] == "waiting_draft_approval":
        logger.info("Draft approval barrier detected! Rendering draft card.")
        await render_draft_card(config, current_state.values)
        return
        
    elif current_state and current_state.next and current_state.next[0] == "waiting_approval_barrier":
        logger.info("Approval barrier detected! Rendering action buttons for CEO.")
        
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
            cl.Action(name="cmo_approve", payload={"value": "approved"}, label="Duyệt và Đăng 🚀"),
            cl.Action(name="cmo_reject", payload={"value": "rejected"}, label="Yêu cầu sửa ✍️")
        ]
        
        sent = await cl.Message(content=approval_card, actions=actions).send()
        track_msg_id(sent.id)
        await associate_messages_with_current_checkpoint(config)

@cl.action_callback("cmo_approve")
async def on_approve(action: cl.Action):
    """Resume LangGraph with approval token."""
    thread_id = cl.user_session.get("thread_id")
    workspace_id = cl.user_session.get("workspace_id")
    product_id = cl.user_session.get("product_id")
    
    config = get_workspace_config(thread_id, workspace_id, product_id)
    
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
    
    config = get_workspace_config(thread_id, workspace_id, product_id)
    
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
        
        with get_session() as db:
            try:
                import tempfile
                tmp_fb = tempfile.mktemp(suffix=".txt")
                with open(tmp_fb, "w", encoding="utf-8") as _f:
                    _f.write(feedback_content)
                fb_key = f"rag/{workspace_id}/feedback_{uuid.uuid4().hex[:8]}.txt"
                upload_file(tmp_fb, fb_key)
                store_document(
                    db=db,
                    workspace_id=workspace_id,
                    file_name=f"cmo_feedback_{uuid.uuid4().hex[:6]}.txt",
                    file_key=fb_key,
                    access_tags=["manager_feedback", "anti_patterns"],
                    file_size_bytes=len(feedback_content.encode()),
                )
                logger.info("Successfully queued CMO feedback vectorization via Celery!")
            except Exception as ve:
                logger.error(f"Failed to vectorize CMO feedback: {ve}", exc_info=True)
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
                    cl.Action(name="cmo_approve", payload={"value": "approved"}, label="Duyệt và Đăng 🚀"),
                    cl.Action(name="cmo_reject", payload={"value": "rejected"}, label="Yêu cầu sửa tiếp ✍️")
                ]
                await cl.Message(content=approval_card, actions=new_actions).send()

    await action.remove()


@cl.action_callback("approve_draft")
async def on_approve_draft(action: cl.Action):
    """CMO approved the draft plan! Resume graph to proceed to creative stage."""
    thread_id = cl.user_session.get("thread_id")
    workspace_id = cl.user_session.get("workspace_id")
    product_id = cl.user_session.get("product_id")
    
    config = get_workspace_config(thread_id, workspace_id, product_id)
    
    sent_info = await cl.Message(content="✅ **Sếp đã duyệt Bản thảo chiến dịch!** Đang chuyển đổi State sạch và khởi chạy Ban Sáng tạo...").send()
    track_msg_id(sent_info.id)
    
    # Update state: set draft_approved = True
    await graph.aupdate_state(config, {"draft_approved": True})
    
    # Resume graph execution
    cb = cl.LangchainCallbackHandler()
    async for event in graph.astream(None, config=config, stream_mode="updates"):
        for node_name, node_update in event.items():
            if node_name == "strategist":
                angle = node_update.get("current_angle", {})
                strat_msg = (
                    f"🧠 **[Phòng Sáng Tạo - Strategist]**\n"
                    f"- Đã nghiên cứu RAG và tự động dán RAG bài học thất bại.\n"
                    f"- **Angle đề xuất:** `{angle.get('angle_name')}`\n"
                    f"- **Nỗi đau đánh trúng:** \"{angle.get('pain_point_focus')}\"\n"
                    f"- **Tập trung:** {angle.get('psychological_angle')}"
                )
                sent = await cl.Message(content=strat_msg).send()
                track_msg_id(sent.id)
                
            elif node_name == "copywriter":
                var = node_update.get("variants", [])[0]
                copy_msg = (
                    f"✍️ **[Phòng Sáng Tạo - Copywriter]**\n"
                    f"- Đã xào nấu và tối ưu hóa kịch bản theo target CPA.\n"
                    f"- **Nội dung nháp Facebook:**\n\n"
                    f"```text\n{var.get('adapted_copy')}\n```\n"
                    f"- **Tags:** {', '.join(var.get('hashtags', []))}"
                )
                sent = await cl.Message(content=copy_msg).send()
                track_msg_id(sent.id)
                
            elif node_name == "guardian":
                logs = node_update.get("feedback_log", [])
                sent = await cl.Message(content=f"🛡️ **[Phòng Sáng Tạo - Brand Guardian]**\n- Kết quả: `{logs[-1]}`").send()
                track_msg_id(sent.id)

    # Once execution finishes, check if paused at waiting_approval_barrier
    await associate_messages_with_current_checkpoint(config)
    current_state = await graph.aget_state(config)
    if current_state and current_state.next and current_state.next[0] == "waiting_approval_barrier":
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
            cl.Action(name="cmo_approve", payload={"value": "approved"}, label="Duyệt và Đăng 🚀"),
            cl.Action(name="cmo_reject", payload={"value": "rejected"}, label="Yêu cầu sửa ✍️")
        ]
        sent = await cl.Message(content=approval_card, actions=actions).send()
        track_msg_id(sent.id)
        await associate_messages_with_current_checkpoint(config)
        
    await action.remove()


@cl.action_callback("reject_draft")
async def on_reject_draft(action: cl.Action):
    """CMO clicked reject draft. Ask for feedback, update state and resume."""
    thread_id = cl.user_session.get("thread_id")
    workspace_id = cl.user_session.get("workspace_id")
    product_id = cl.user_session.get("product_id")
    
    config = get_workspace_config(thread_id, workspace_id, product_id)
    
    res = await cl.AskUserMessage(content="Sếp cần điều chỉnh gì cho Bản thảo chiến dịch? Nhập ý kiến phản hồi tại đây:").send()
    if res:
        feedback_text = res["output"]
        track_msg_id(res["id"])
        
        sent_info = await cl.Message(content=f"✍️ Gửi phản hồi đàm phán: *\"{feedback_text}\"*...").send()
        track_msg_id(sent_info.id)
        
        user_msg = HumanMessage(content=feedback_text, additional_kwargs={"cl_msg_id": res["id"]})
        state_update = {
            "messages": [user_msg],
            "draft_approved": False
        }
        await graph.aupdate_state(config, state_update)
        
        async for event in graph.astream(None, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                if node_name == "negotiator":
                    new_msgs = node_update.get("messages", [])
                    if new_msgs:
                        ans_msg = new_msgs[-1].content
                        sent_msg = await cl.Message(content=ans_msg).send()
                        track_msg_id(sent_msg.id)
                        
        await associate_messages_with_current_checkpoint(config)
        new_state = await graph.aget_state(config)
        await render_draft_card(config, new_state.values)
        
    await action.remove()


@cl.action_callback("rewind_draft")
async def on_rewind_draft(action: cl.Action):
    """Time Travel: Rewind the graph state to a past checkpoint."""
    checkpoint_id = action.payload.get("value")
    thread_id = cl.user_session.get("thread_id")
    workspace_id = cl.user_session.get("workspace_id")
    product_id = cl.user_session.get("product_id")
    
    config = get_workspace_config(thread_id, workspace_id, product_id)
    
    logger.info(f"Time Travel Action received: Rewinding to checkpoint {checkpoint_id}")
    
    # 1. Fetch checkpoints list to identify the future checkpoints that will be aborted
    future_checkpoint_ids = []
    found_target = False
    
    history = []
    async for state in graph.aget_state_history(config):
        history.append(state)
        
    # Reverse history to oldest first
    history.reverse()
    
    for state in history:
        chk_id = state.config["configurable"].get("checkpoint_id")
        if found_target:
            future_checkpoint_ids.append(chk_id)
        if chk_id == checkpoint_id:
            found_target = True
            
    logger.info(f"Target checkpoint: {checkpoint_id}. Aborting checkpoints: {future_checkpoint_ids}")
    
    # 2. Extract and dim any UI messages corresponding to future checkpoints
    mappings = cl.user_session.get("checkpoint_ui_mappings") or {}
    for fc_id in future_checkpoint_ids:
        msg_ids = mappings.get(fc_id) or []
        for msg_id in msg_ids:
            try:
                # Find matching text from history for content restoration
                original_text = ""
                for state in history:
                    if state.config["configurable"].get("checkpoint_id") == fc_id:
                        msgs = state.values.get("messages", [])
                        if msgs:
                            original_text = msgs[-1].content
                            
                formatted_content = f'<div class="aborted-message-wrapper">*(Dòng thời gian đã hủy)*<br/>{original_text}</div>'
                await cl.Message(id=msg_id, content=formatted_content, actions=[]).update()
                logger.info(f"Dimmed future message ID: {msg_id}")
            except Exception as me:
                logger.error(f"Failed to dim message {msg_id}: {me}")
                
    # 3. Send visual Divider
    divider_text = (
        f"⚡ **🔀 DÒNG THỜI GIAN ĐÃ RẼ NHÁNH TẠI ĐÂY**\n"
        f"*(Đã tua ngược về phiên bản Draft trước đó)*"
    )
    sent_div = await cl.Message(content=divider_text).send()
    track_msg_id(sent_div.id)
    
    # 4. Fork the state in LangGraph Checkpointer
    target_config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id
        }
    }
    target_state = await graph.aget_state(target_config)
    
    new_values = target_state.values.copy()
    new_values["draft_approved"] = False
    
    await graph.aupdate_state(config, new_values)
    
    # 5. Render the new Draft Card for the branched state
    new_state = await graph.aget_state(config)
    await render_draft_card(config, new_state.values)
    
    await action.remove()

