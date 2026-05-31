# core/ai_clients/serpapi_client.py
import os
import logging
from typing import Dict, List, Any
import serpapi

logger = logging.getLogger("serpapi_client")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# CUSTOM SERPAPI SDK EXCEPTIONS
# ---------------------------------------------------------------------------

class SerpApiSDKError(Exception):
    """Base exception for SerpApi SDK operations."""
    def __init__(self, message: str, status_code: int = None, error_payload: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_payload = error_payload

class SerpApiBadRequestError(SerpApiSDKError):
    """400 - Bad Request"""

class SerpApiUnauthorizedError(SerpApiSDKError):
    """401 - Unauthorized"""

class SerpApiForbiddenError(SerpApiSDKError):
    """403 - Forbidden"""

class SerpApiNotFoundError(SerpApiSDKError):
    """404 - Not Found"""

class SerpApiGoneError(SerpApiSDKError):
    """410 - Gone"""

class SerpApiTooManyRequestsError(SerpApiSDKError):
    """429 - Too Many Requests"""

class SerpApiServerError(SerpApiSDKError):
    """500, 503 - Server Error"""


def _raise_custom_exception(e: Exception):
    """
    Analyzes the SerpApi SDK exception and maps it to a highly descriptive custom exception class.
    """
    if isinstance(e, serpapi.HTTPError):
        status_code = e.status_code
        err_msg = getattr(e, "error", None) or str(e)
        payload = {"error": err_msg}
        
        if status_code == 400:
            raise SerpApiBadRequestError(f"SerpApi 400 Bad Request: {err_msg}", status_code, payload)
        elif status_code == 401:
            raise SerpApiUnauthorizedError(f"SerpApi 401 Unauthorized: {err_msg}", status_code, payload)
        elif status_code == 403:
            raise SerpApiForbiddenError(f"SerpApi 403 Forbidden: {err_msg}", status_code, payload)
        elif status_code == 404:
            raise SerpApiNotFoundError(f"SerpApi 404 Not Found: {err_msg}", status_code, payload)
        elif status_code == 410:
            raise SerpApiGoneError(f"SerpApi 410 Gone: {err_msg}", status_code, payload)
        elif status_code == 429:
            raise SerpApiTooManyRequestsError(f"SerpApi 429 Too Many Requests: {err_msg}", status_code, payload)
        elif status_code in (500, 503):
            raise SerpApiServerError(f"SerpApi {status_code} Server Error: {err_msg}", status_code, payload)
        else:
            raise SerpApiSDKError(f"SerpApi HTTP Error {status_code}: {err_msg}", status_code, payload)
    elif isinstance(e, serpapi.APIKeyNotProvided):
        raise SerpApiUnauthorizedError("SerpApi 401 Unauthorized: API key not provided.", 401, {"error": "API key not provided"})
    elif isinstance(e, serpapi.TimeoutError):
        raise SerpApiServerError("SerpApi Timeout Error: Request timed out.", 504, {"error": "Request timed out"})
    else:
        raise SerpApiSDKError(f"SerpApi SDK Error: {str(e)}")


def get_serpapi_key(workspace_id: str) -> str:
    """
    Retrieves the SerpApi API key from workspace integrations or environment variables.
    """
    from core.utils import get_integration_config
    configs = get_integration_config(workspace_id, "serpapi")
    api_key = configs.get("api_key") or os.getenv("SERPAPI_API_KEY")
    return api_key.strip() if api_key else ""

def search_youtube(
    query: str, 
    workspace_id: str, 
    hl: str = "vi", 
    gl: str = "vn", 
    location: str = "Vietnam"
) -> Dict[str, Any]:
    """
    Searches YouTube via SerpApi Python SDK 'youtube' engine.
    Includes robust fallback mock data if SerpApi is not configured.
    """
    api_key = get_serpapi_key(workspace_id)
    if not api_key:
        logger.warning("[SerpApi] API Key not found. Utilizing mock fallback search results.")
        return _get_mock_search_results(query)
        
    try:
        logger.info(f"[SerpApi] Calling YouTube search for query: '{query}'...")
        client = serpapi.Client(api_key=api_key)
        data = client.search({
            "engine": "youtube",
            "search_query": query,
            "hl": hl,
            "gl": gl,
            "location": location
        })
        
        if "error" in data or "video_results" not in data:
            err_msg = data.get("error", "Unknown error")
            logger.warning(f"[SerpApi] Search returned error or missing results: {err_msg}. Utilizing fallback.")
            return _get_mock_search_results(query)
        return dict(data)
    except Exception as e:
        logger.error(f"[SerpApi] YouTube search failed: {e}. Utilizing fallback mock data.")
        try:
            _raise_custom_exception(e)
        except Exception as mapped_err:
            logger.error(f"[SerpApi] Detailed SDK Exception mapping: {type(mapped_err).__name__} - {mapped_err}")
        return _get_mock_search_results(query)

def get_youtube_transcript(
    video_id: str, 
    workspace_id: str, 
    language_code: str = "vi"
) -> Dict[str, Any]:
    """
    Fetches YouTube video transcript via SerpApi Python SDK 'youtube_video_transcript' engine.
    Includes fallback mock transcript data.
    """
    api_key = get_serpapi_key(workspace_id)
    if not api_key:
        logger.warning(f"[SerpApi] API Key not found. Utilizing mock fallback transcript for video {video_id}.")
        return _get_mock_transcript(video_id)
        
    try:
        logger.info(f"[SerpApi] Fetching transcript for video: {video_id}...")
        client = serpapi.Client(api_key=api_key)
        data = client.search({
            "engine": "youtube_video_transcript",
            "v": video_id,
            "language_code": language_code
        })
        
        if "error" in data or "transcript" not in data:
            err_msg = data.get("error", "Unknown error")
            logger.warning(f"[SerpApi] Transcript returned error or missing transcript: {err_msg}. Utilizing fallback.")
            return _get_mock_transcript(video_id)
        return dict(data)
    except Exception as e:
        logger.error(f"[SerpApi] Transcript fetch failed for video {video_id}: {e}. Utilizing fallback.")
        try:
            _raise_custom_exception(e)
        except Exception as mapped_err:
            logger.error(f"[SerpApi] Detailed SDK Exception mapping: {type(mapped_err).__name__} - {mapped_err}")
        return _get_mock_transcript(video_id)

def get_youtube_comments(
    video_id: str, 
    workspace_id: str
) -> Dict[str, Any]:
    """
    Fetches YouTube comments via SerpApi Python SDK 'youtube_comments' engine.
    Includes fallback mock comments.
    """
    api_key = get_serpapi_key(workspace_id)
    if not api_key:
        logger.warning(f"[SerpApi] API Key not found. Utilizing mock fallback comments for video {video_id}.")
        return _get_mock_comments(video_id)
        
    try:
        logger.info(f"[SerpApi] Fetching comments for video: {video_id}...")
        client = serpapi.Client(api_key=api_key)
        data = client.search({
            "engine": "youtube_comments",
            "v": video_id
        })
        
        if "error" in data or "comments" not in data:
            err_msg = data.get("error", "Unknown error")
            logger.warning(f"[SerpApi] Comments returned error or missing comments: {err_msg}. Utilizing fallback.")
            return _get_mock_comments(video_id)
        return dict(data)
    except Exception as e:
        logger.error(f"[SerpApi] Comments fetch failed for video {video_id}: {e}. Utilizing fallback.")
        try:
            _raise_custom_exception(e)
        except Exception as mapped_err:
            logger.error(f"[SerpApi] Detailed SDK Exception mapping: {type(mapped_err).__name__} - {mapped_err}")
        return _get_mock_comments(video_id)


# ---------------------------------------------------------------------------
# FALLBACK MOCK DATA GENERATORS
# ---------------------------------------------------------------------------

def _get_mock_search_results(query: str) -> Dict[str, Any]:
    return {
        "video_results": [
            {
                "title": f"Hướng dẫn tối ưu CPA quảng cáo đột phá cho {query}",
                "link": "https://www.youtube.com/watch?v=mockvid0001",
                "video_id": "mockvid0001",
                "channel": {"name": "Học Viện Marketing Tech"},
                "description": f"Video chia sẻ bí quyết viết kịch bản và chạy quảng cáo {query} hiệu quả, tối ưu CPA vượt mong đợi."
            },
            {
                "title": f"Sai lầm đốt tiền khi triển khai {query} - Bài học xương máu",
                "link": "https://www.youtube.com/watch?v=mockvid0002",
                "video_id": "mockvid0002",
                "channel": {"name": "CMO Thực Chiến"},
                "description": "Chia sẻ các kịch bản quảng cáo thất bại và cách khắc phục để đạt CPA target dưới ngưỡng biên lợi nhuận."
            },
            {
                "title": f"Review G-Agent Tech: Tự động hóa 80% phòng Creative",
                "link": "https://www.youtube.com/watch?v=mockvid0003",
                "video_id": "mockvid0003",
                "channel": {"name": "Review Công Nghệ"},
                "description": "Đánh giá chi tiết Marketing Agent OS phần mềm tối ưu ads tự trị bằng AI Agents LangGraph."
            }
        ]
    }

def _get_mock_transcript(video_id: str) -> Dict[str, Any]:
    # Custom transcripts based on mock video ID
    if video_id == "mockvid0001":
        snippet = (
            "Chào mừng mọi người đã quay trở lại. Hôm nay tôi sẽ hướng dẫn các bạn cách tối ưu chi phí chuyển đổi CPA. "
            "Nếu bạn đang chạy Ads mà CPA tăng vọt, hãy xem ngay 3 giây đầu tiên của video. Hook của bạn phải đánh thẳng vào "
            "vấn đề của khách hàng. Hãy mua ngay phần mềm Marketing Agent OS của G-Agent Tech để tự động hóa 80% thời gian. "
            "Chúng tôi cam kết giúp bạn giảm 50% CPA trong tuần đầu tiên. Hãy nhấn vào link dưới mô tả để đăng ký dùng thử ngay hôm nay!"
        )
    elif video_id == "mockvid0002":
        snippet = (
            "Có rất nhiều người đang chạy quảng cáo sai lầm. Đốt hàng trăm triệu nhưng không ra đơn. Sai lầm lớn nhất "
            "là kịch bản quá chung chung, không có Call-to-action cụ thể. Rất nhiều kịch bản thất bại vì sến súa, "
            "không có điểm nhấn hoặc cam kết quá đà 100% không căn cứ. Hãy thiết lập một quy trình an toàn ngân sách "
            "để bảo vệ dòng tiền của bạn ngay hôm nay."
        )
    else:
        snippet = (
            "Hôm nay mình sẽ review một công cụ cực hot đó là Marketing Agent OS của G-Agent Tech. "
            "Điểm nổi bật của phần mềm này là sử dụng hệ thống Multi-Agent LangGraph tự động tối ưu hóa CPA. "
            "Nó giúp giải phóng 80% thời gian duyệt kịch bản của các sếp CMO bận rộn. Bạn không cần bận tâm về "
            "Agency thủ công nữa. Liên hệ ngay G-Agent Tech để nhận ưu đãi dùng thử miễn phí."
        )
        
    return {
        "transcript": [
            {
                "start_ms": 200,
                "end_ms": 10000,
                "snippet": snippet,
                "start_time_text": "0:00"
            }
        ]
    }

def _get_mock_comments(video_id: str) -> Dict[str, Any]:
    if video_id == "mockvid0001":
        comments = [
            {"text": "Bí quyết này quá hay, mình đã áp dụng và giảm được kha khá CPA!", "author": "Hải Nam"},
            {"text": "Phần mềm Marketing Agent OS dùng thử ở đâu thế admin ơi?", "author": "Vinh Nguyễn"},
            {"text": "Cơ chế tự động hóa LangGraph này có khó cấu hình không ạ?", "author": "Khánh Linh"},
            {"text": "Tôi đã dùng thử G-Agent Tech và thấy tiết kiệm được rất nhiều thời gian duyệt bài.", "author": "Minh Trần"},
            {"text": "Cam kết giảm 50% CPA nghe hơi quá nhưng dùng thử xem thế nào.", "author": "Hoàng Anh"}
        ]
    elif video_id == "mockvid0002":
        comments = [
            {"text": "Bài học rất thực tế. K kịch bản quảng cáo cũ của mình đúng là sến súa thật, hèn gì CPA cao vút.", "author": "Quốc Huy"},
            {"text": "Chạy ads bây giờ đắt quá, đúng là bị phụ thuộc agency mệt mỏi.", "author": "Thu Trang"},
            {"text": "Lỗi cấm từ khóa của Facebook quét gắt thật, có cách nào tự động kiểm tra trước không?", "author": "Tuấn Anh"},
            {"text": "Video rất bổ ích, mong kênh ra thêm các anti-pattern cần tránh nữa.", "author": "Hương Giang"},
            {"text": "Nên tập trung vào số liệu thực tế thay vì quảng cáo hoa mỹ.", "author": "Đức Mạnh"}
        ]
    else:
        comments = [
            {"text": "Review chi tiết quá. Mình cũng đang tìm giải pháp giải phóng thời gian cho phòng creative.", "author": "Văn Dũng"},
            {"text": "Marketing Agent OS giá bao nhiêu vậy G-Agent Tech?", "author": "Thanh Hằng"},
            {"text": "Công cụ này đúng là điểm neo kinh tế tuyệt vời cho doanh nghiệp nhỏ.", "author": "Sơn Tùng"},
            {"text": "Chạy thử nghiệm LangGraph thấy rất ổn định, hệ thống online 100%.", "author": "Mai Phương"},
            {"text": "Giao diện Chainlit trực quan, dễ dùng cho CMO duyệt camp.", "author": "Ngọc Hải"}
        ]
        
    return {"comments": comments}
