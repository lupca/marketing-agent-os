# core/integrations/video_client.py
"""
Client module for communicating with Marketing Video Agent API.
Handles job submission and status polling.
"""
import logging
import requests
from typing import Optional, Dict, Any

from config.settings import VIDEO_AGENT_URL, VIDEO_AGENT_API_KEY

logger = logging.getLogger("video_client")

def submit_video_job(
    variant_id: str,
    video_script: str,
    platform: str,
    workspace_id: str,
    campaign_id: str,
    brand_name: str = "",
    brand_voice: str = "",
    campaign_name: str = "",
    campaign_objective: str = "",
    angle_name: str = "",
    extra_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Submit a video generation job to Video Agent.
    Uses the /api/jobs/from-tmcp endpoint (Leader Agent pipeline).
    
    Returns: {"job_id": int, "status": str}
    """
    # Build payload structured to match Video Agent's TMCPPayload schema
    payload = {
        "source_id": str(variant_id),
        "brand_context": {
            "brand_name": brand_name or "Default Brand",
            "tone_of_voice": brand_voice or "Neutral",
            "brand_colors": []
        },
        "campaign_context": {
            "campaign_name": campaign_name or "Default Campaign",
            "target_audience": "",
            "objective": campaign_objective or "LEAD_GEN"
        },
        "variant_data": {
            "title": f"Video variant {variant_id[:8]}",
            "script_content": video_script,
            "media_hints": [],
            "suggested_duration": 15
        },
        "title": f"Video variant {variant_id[:8]}",
        "script_content": video_script,
        "media_hints": [],
        "suggested_duration": 15,
        "master_contents_brief": "",
        "content_brief_context": {
            "angle_name": angle_name or "",
            "funnel_stage": "",
            "psychological_angle": "",
            "pain_point_focus": "",
            "key_message_variation": "",
            "call_to_action_direction": "",
            "brief": ""
        },
        "callback_url": "",
        "facebook_page_id": "",
        "upload_config": {}
    }
    
    if extra_config:
        payload.update(extra_config)
    
    headers = {"X-TMCP-Key": VIDEO_AGENT_API_KEY}
    url = f"{VIDEO_AGENT_URL.rstrip('/')}/api/jobs/from-tmcp"
    
    logger.info(f"Submitting video job to {url} for variant {variant_id}...")
    resp = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"job_id": data["id"], "status": data["status"]}


def get_job_status(job_id: int) -> Dict[str, Any]:
    """
    Poll Video Agent for job status.
    Returns: {"status": str, "result_url": Optional[str], "progress": int, "error": Optional[str]}
    """
    headers = {"X-TMCP-Key": VIDEO_AGENT_API_KEY}
    url = f"{VIDEO_AGENT_URL.rstrip('/')}/api/jobs/{job_id}"
    
    resp = requests.get(
        url,
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "status": data.get("status"),
        "result_url": data.get("result_url"),
        "progress": data.get("progress_percent", 0),
        "error": data.get("error_message"),
    }
