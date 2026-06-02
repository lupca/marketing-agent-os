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
        logger.error("[SerpApi] API Key not found.")
        raise SerpApiUnauthorizedError("API key not provided for SerpApi Youtube Search.")
        
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
            raise SerpApiSDKError(f"Search returned error or missing results: {err_msg}")
        return dict(data)
    except Exception as e:
        logger.error(f"[SerpApi] YouTube search failed: {e}.")
        try:
            _raise_custom_exception(e)
        except Exception as mapped_err:
            logger.error(f"[SerpApi] Detailed SDK Exception mapping: {type(mapped_err).__name__} - {mapped_err}")
            raise mapped_err

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
        logger.error(f"[SerpApi] API Key not found for transcript fetch.")
        raise SerpApiUnauthorizedError("API key not provided for SerpApi Youtube Transcript.")
        
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
            raise SerpApiSDKError(f"Transcript returned error or missing transcript: {err_msg}")
        return dict(data)
    except Exception as e:
        logger.error(f"[SerpApi] Transcript fetch failed for video {video_id}: {e}.")
        try:
            _raise_custom_exception(e)
        except Exception as mapped_err:
            logger.error(f"[SerpApi] Detailed SDK Exception mapping: {type(mapped_err).__name__} - {mapped_err}")
            raise mapped_err

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
        logger.error(f"[SerpApi] API Key not found for comments fetch.")
        raise SerpApiUnauthorizedError("API key not provided for SerpApi Youtube Comments.")
        
    try:
        logger.info(f"[SerpApi] Fetching comments for video: {video_id}...")
        client = serpapi.Client(api_key=api_key)
        data = client.search({
            "engine": "youtube_comments",
            "v": video_id
        })
        
        if "error" in data or "comments" not in data:
            err_msg = data.get("error", "Unknown error")
            raise SerpApiSDKError(f"Comments returned error or missing comments: {err_msg}")
        return dict(data)
    except Exception as e:
        logger.error(f"[SerpApi] Comments fetch failed for video {video_id}: {e}.")
        try:
            _raise_custom_exception(e)
        except Exception as mapped_err:
            logger.error(f"[SerpApi] Detailed SDK Exception mapping: {type(mapped_err).__name__} - {mapped_err}")
            raise mapped_err



