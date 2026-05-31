# core/market_intelligence.py
import json
import logging
import uuid
from typing import Dict, List, Any
from sqlalchemy.orm import Session

from core.ai_clients.serpapi_client import search_youtube, get_youtube_transcript, get_youtube_comments
from core.ai_clients.llm_client import generate_text
from core.utils import parse_llm_json
from core.document_service import process_and_store_document
from core.storage import upload_file

logger = logging.getLogger("market_intelligence")
logging.basicConfig(level=logging.INFO)

LLM_PRE_PROCESS_PROMPT = """
Bạn là Chuyên gia Tình Báo Thị Trường. Nhiệm vụ của bạn là phân tích kịch bản đối thủ và các bình luận để phục vụ cho phòng Creative viết kịch bản quảng cáo tối ưu CPA.

TIÊU ĐỀ VIDEO: {video_title}
THOẠI VIDEO (TRANSCRIPT):
{transcript_text}

BÌNH LUẬN CỦA KHÁCH HÀNG:
{comments_text}

YÊU CẦU PHÂN TÍCH:
1. Xác định xem video này có phải là 'video rác' không (is_trash: true/false). Định nghĩa video rác: KHÔNG có Call-To-Action (kêu gọi mua hàng, đăng ký, click link, liên hệ), KHÔNG giới thiệu giải pháp sản phẩm cụ thể, hoặc chỉ là video giải trí thuần túy không mang tính chất quảng cáo/thương mại.
2. Bóc tách Hook (phần giật tít, giữ chân người dùng trong 3-5 giây đầu). Phân loại hook_type (ví dụ: 'gây tò mò', 'nêu giải pháp', 'đánh vào nỗi sợ', 'hài hước').
3. Phân tích Sentiment từ bình luận (tính toán tỷ lệ phần trăm Tích cực, Trung lập, Tiêu cực) và trích xuất danh sách các điểm đau (Pain-Points) thực tế của khách hàng từ bình luận hoặc kịch bản.
4. Viết một báo cáo Markdown chi tiết tóm tắt kịch bản đối thủ, bao gồm:
   - Thông tin chung (Tiêu đề, Kênh, Link).
   - Đánh giá Hook & Phân tích Sentiment.
   - Các Pain-Points đúc kết được.
   - Nội dung kịch bản thoại sạch đã lọc rác.

Bạn BẮT BUỘC phải trả về dữ liệu định dạng JSON hợp lệ theo schema sau:
{{
  "is_trash": boolean,
  "hook": "nội dung hook bóc tách được",
  "hook_type": "gây tò mò | nêu giải pháp | đánh vào nỗi sợ | hài hước | khác",
  "sentiment": {{
    "positive_pct": number,
    "neutral_pct": number,
    "negative_pct": number
  }},
  "pain_points": ["điểm đau 1", "điểm đau 2", "điểm đau 3"],
  "markdown_report": "Nội dung báo cáo markdown chi tiết..."
}}
"""

def fetch_and_process_market_data(
    db: Session,
    workspace_id: str,
    query: str,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Core Pipeline:
    1. YouTube Search qua SerpApi
    2. Lưu raw JSON vào Cold Storage (market-intel-raw bucket)
    3. Với mỗi video: lấy transcript & comments
    4. Tiền xử lý bằng LLM (lọc rác, bóc hooks, phân tích sentiment & pain-points)
    5. Upload báo cáo phân tích Markdown ảo vào pgvector RAG (access_tags=["market_intel"])
    """
    logger.info(f"[MarketIntelligence] Starting pipeline for query: '{query}' in workspace: {workspace_id}")
    
    # 1. Search YouTube
    search_results = search_youtube(query, workspace_id)
    video_results = search_results.get("video_results", [])
    
    if not video_results:
        logger.warning("[MarketIntelligence] No YouTube search results found.")
        return []
        
    # Save search raw JSON to cold storage
    search_filename = f"youtube_search_{uuid.uuid4().hex[:8]}.json"
    _save_raw_to_cold_storage(search_results, search_filename)
    
    processed_videos = []
    
    for idx, video in enumerate(video_results[:limit]):
        video_id = video.get("video_id")
        video_title = video.get("title", "Unknown Title")
        video_link = video.get("link", "")
        channel_name = video.get("channel", {}).get("name", "Unknown Channel")
        
        if not video_id:
            continue
            
        logger.info(f"[MarketIntelligence] Processing video {idx+1}/{limit}: {video_title} (ID: {video_id})")
        
        # 2. Fetch Transcript
        transcript_res = get_youtube_transcript(video_id, workspace_id)
        transcript_list = transcript_res.get("transcript", [])
        transcript_text = " ".join([t.get("snippet", "") for t in transcript_list])
        
        # 3. Fetch Comments
        comments_res = get_youtube_comments(video_id, workspace_id)
        comments_list = comments_res.get("comments", [])
        comments_text = "\n".join([f"- {c.get('author', 'User')}: {c.get('text', '')}" for c in comments_list])
        
        # Save raw video data (comments + transcript + metadata) to cold storage
        raw_video_data = {
            "video_metadata": video,
            "transcript_raw": transcript_res,
            "comments_raw": comments_res
        }
        video_filename = f"youtube_video_{video_id}.json"
        _save_raw_to_cold_storage(raw_video_data, video_filename)
        
        # 4. LLM Pre-processing
        prompt = LLM_PRE_PROCESS_PROMPT.format(
            video_title=video_title,
            transcript_text=transcript_text or "(Không có transcript)",
            comments_text=comments_text or "(Không có bình luận)"
        )
        
        try:
            logger.info(f"[MarketIntelligence] Analyzing video '{video_id}' with LLM...")
            analysis_raw = generate_text(
                prompt=prompt,
                system_prompt="Bạn là AI Tình Báo Thị Trường chuyên nghiệp. Hãy trả về JSON hợp lệ theo yêu cầu.",
                json_format=True,
                workspace_id=workspace_id
            )
            analysis_data = parse_llm_json(analysis_raw)
        except Exception as err:
            logger.error(f"[MarketIntelligence] LLM Analysis failed for video {video_id}: {err}")
            continue
            
        is_trash = analysis_data.get("is_trash", False)
        if is_trash:
            logger.info(f"[MarketIntelligence] Video {video_id} is classified as TRASH (No CTA / Commercial intent). Skipping ingestion.")
            continue
            
        # 5. Save refined analysis Markdown to pgvector RAG
        markdown_content = analysis_data.get("markdown_report", "")
        if not markdown_content:
            # Fallback if markdown_report is empty
            markdown_content = (
                f"# Phân Tích Kịch Bản Đối Thủ: {video_title}\n"
                f"- **Kênh:** {channel_name}\n"
                f"- **Link:** {video_link}\n"
                f"- **Hook:** {analysis_data.get('hook', 'N/A')} (Loại: {analysis_data.get('hook_type', 'N/A')})\n"
                f"- **Sentiment:** Tích cực: {analysis_data.get('sentiment', {}).get('positive_pct', 0)}%, Tiêu cực: {analysis_data.get('sentiment', {}).get('negative_pct', 0)}%\n"
                f"- **Pain Points:** {', '.join(analysis_data.get('pain_points', []))}\n\n"
                f"## Lời thoại sạch:\n{transcript_text}"
            )
            
        file_name = f"market_intel_youtube_{video_id}.md"
        file_bytes = markdown_content.encode("utf-8")
        
        # Pass deep analysis parameters to RAG Document & Chunks metadata
        metadata = {
            "source": "youtube",
            "video_id": video_id,
            "video_title": video_title,
            "channel_name": channel_name,
            "video_link": video_link,
            "hook": analysis_data.get("hook", ""),
            "hook_type": analysis_data.get("hook_type", ""),
            "sentiment": analysis_data.get("sentiment", {}),
            "pain_points": analysis_data.get("pain_points", [])
        }
        
        logger.info(f"[MarketIntelligence] Ingesting analysis document to RAG: {file_name}")
        try:
            doc_info = process_and_store_document(
                db=db,
                workspace_id=workspace_id,
                file_bytes=file_bytes,
                file_name=file_name,
                access_tags=["market_intel"],
                metadata=metadata
            )
            
            processed_videos.append({
                "video_id": video_id,
                "title": video_title,
                "channel": channel_name,
                "document_id": doc_info.get("document_id"),
                "analysis": analysis_data
            })
            
            logger.info(f"[MarketIntelligence] Successfully processed and stored: {video_title}")
        except Exception as doc_err:
            logger.error(f"[MarketIntelligence] Ingestion failed for video {video_id}: {doc_err}")
            
    return processed_videos

def _save_raw_to_cold_storage(raw_data: dict, filename: str):
    """
    Saves raw dictionary locally and uploads to MinIO bucket 'market-intel-raw' as cold storage.
    """
    import tempfile
    import os
    
    try:
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"[MarketIntelligence] Uploading raw JSON to cold storage: raw/{filename}...")
        upload_file(temp_path, f"raw/{filename}", bucket_name="market-intel-raw")
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
            os.rmdir(temp_dir)
    except Exception as e:
        logger.error(f"[MarketIntelligence] Cold storage raw save failed: {e}")
