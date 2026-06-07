import logging
import json
import uuid
from core.celery_app import celery_app
from core.dependencies import get_session
from core.models import Workspace, ProductService
from core.ai_clients.serpapi_client import search_youtube
from core.ai_clients.llm_client import generate_text
from core.utils import parse_llm_json
from core.decision_logger import log_decision

logger = logging.getLogger("radar_worker_tasks")

@celery_app.task(
    bind=True,
    name="workers.radar_worker.tasks.radar_market_first_cron",
    queue="social_publisher",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def radar_market_first_cron(self):
    """
    Cron job running daily at 8:00 AM.
    Scrapes competitor YouTube channels, detects Trends/Gaps, compares with internal products,
    and logs Alert decisions to PostgreSQL db for CMO attention.
    """
    with get_session() as db:
        try:
            logger.info("[radar_market_first_cron] Starting daily radar search...")
            workspaces = db.query(Workspace).all()
            for ws in workspaces:
                # 1. Fetch products for this workspace
                products = db.query(ProductService).filter_by(workspace_id=ws.id).all()
                if not products:
                    continue
                product_names = [p.name for p in products]
                
                # 2. Search YouTube via SerpApi for competitor trends related to the first product
                query = f"competitor trends {product_names[0]}"
                logger.info(f"[radar_market_first_cron] Querying SerpApi for query '{query}' in workspace {ws.id}...")
                search_results = search_youtube(query, str(ws.id))
                video_results = search_results.get("video_results", [])
                if not video_results:
                    logger.warning(f"[radar_market_first_cron] No video results found for radar query.")
                    continue
                
                # Format competitor videos summary
                competitor_videos = []
                for v in video_results[:5]:
                    competitor_videos.append({
                        "title": v.get("title"),
                        "channel": v.get("channel", {}).get("name"),
                        "views": v.get("views", 0),
                        "snippet": v.get("description", "")
                    })
                
                # 3. Call LLM to detect Trends or Gap relative to our products
                llm_prompt = f"""
                Bạn là Giám sát Radar Tình Báo Thị Trường. Hãy phân tích danh sách các video quảng cáo thịnh hành của đối thủ dưới đây và đối chiếu với danh sách sản phẩm hiện có của chúng ta để tìm ra khoảng trống thị trường (Gap) hoặc xu hướng nổi bật (Trend) có thể khai thác.
                
                SẢN PHẨM CỦA CHÚNG TA:
                {json.dumps(product_names, ensure_ascii=False, indent=2)}
                
                VIDEO ĐỐI THỦ THỊNH HÀNH:
                {json.dumps(competitor_videos, ensure_ascii=False, indent=2)}
                
                YÊU CẦU:
                Xác định xem có xu hướng (Trend) hoặc khoảng trống thị trường (Gap) nào liên quan đến sản phẩm của chúng ta không.
                Nếu có, hãy đưa ra một cảnh báo (Alert) chi tiết hướng phát triển kịch bản quảng cáo mới.
                Định dạng trả về bắt buộc là JSON:
                {{
                  "has_trend": boolean,
                  "trend_description": "mô tả xu hướng / gap phát hiện được",
                  "matching_product": "tên sản phẩm của chúng ta khớp với xu hướng",
                  "cmo_alert_message": "nội dung cảnh báo ngắn gọn gửi cho CMO duyệt chiến dịch (khoảng 2-3 câu, nêu bật số liệu/lý do)"
                }}
                """
                
                logger.info(f"[radar_market_first_cron] Calling LLM to analyze trends/gaps...")
                analysis_raw = generate_text(
                    prompt=llm_prompt,
                    system_prompt="Bạn là Market Radar Advisor. Trả về JSON hợp lệ.",
                    json_format=True,
                    workspace_id=str(ws.id)
                )
                analysis_data = parse_llm_json(analysis_raw)
                
                if analysis_data.get("has_trend", False):
                    alert_msg = f"🚨 **[Market Radar Alert]** {analysis_data.get('cmo_alert_message')}"
                    logger.warning(f"[radar_market_first_cron] TREND DETECTED! Alert: {alert_msg}")
                    
                    # 4. Ghi log alert vào database (sử dụng log_decision)
                    log_decision(
                        workspace_id=ws.id,
                        agent_name="Market Radar Agent",
                        action="Detect Market Trend/Gap",
                        decision_status="alert",
                        reason=alert_msg,
                        metadata={
                            "trend_description": analysis_data.get("trend_description"),
                            "matching_product": analysis_data.get("matching_product"),
                            "raw_analysis": analysis_data
                        }
                    )
            
            logger.info("[radar_market_first_cron] Finished daily radar search successfully.")
            return {"status": "success"}
        except Exception as exc:
            logger.error(f"[radar_market_first_cron] Cron task failed: {exc}", exc_info=True)
            db.rollback()
            raise self.retry(exc=exc)
