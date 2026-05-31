# core/ai_clients/upload_post_client.py
import os
import logging
import requests

logger = logging.getLogger("upload_post_client")
logging.basicConfig(level=logging.INFO)

class UploadPostError(Exception):
    """Base exception class for Upload-Post API operations."""
    pass

class UploadPostAuthError(UploadPostError):
    """Exception raised when API key is unauthorized or session has expired (401, 403)."""
    pass

class UploadPostValidationError(UploadPostError):
    """Exception raised when input validation fails or format is incorrect (400)."""
    pass

class UploadPostRateLimitError(UploadPostError):
    """Exception raised when the request is rate-limited (429)."""
    pass

class UploadPostServerError(UploadPostError):
    """Exception raised when the server responds with a server error (50x)."""
    pass

def handle_response(response):
    """Helper function to raise classified exceptions based on the HTTP response."""
    status = response.status_code
    if 200 <= status < 300:
        try:
            return response.json()
        except Exception:
            return {"success": True, "text": response.text}
    
    # Error classification
    try:
        err_data = response.json()
        err_msg = err_data.get("error") or err_data.get("message") or response.text
    except Exception:
        err_msg = response.text
        
    if status in (401, 403):
        raise UploadPostAuthError(f"Authentication failed ({status}): {err_msg}")
    elif status == 400:
        raise UploadPostValidationError(f"Validation failed (400): {err_msg}")
    elif status == 429:
        raise UploadPostRateLimitError(f"Rate limited (429): {err_msg}")
    elif status >= 500:
        raise UploadPostServerError(f"Server error ({status}): {err_msg}")
    else:
        raise UploadPostError(f"API call failed with status {status}: {err_msg}")

def upload_photos(api_key: str, user: str, platforms: list, photos: list, title: str = None, description: str = None, facebook_page_id: str = None, additional_params: dict = None) -> dict:
    """
    Uploads photos to various platforms via Upload-Post API.
    
    :param api_key: Authorization API key
    :param user: User identifier (profile username, e.g., 'topvnsport')
    :param platforms: List of platforms, e.g., ['facebook']
    :param photos: List of local absolute file paths to photos
    :param title: Title/caption of the post
    :param description: Optional extended description/commentary
    :param facebook_page_id: Optional target Facebook page ID
    :param additional_params: Any other parameters
    """
    url = "https://api.upload-post.com/api/upload_photos"
    headers = {
        "Authorization": f"Apikey {api_key}"
    }
    
    form_data = []
    form_data.append(("user", user))
    if title:
        form_data.append(("title", title))
    if description:
        form_data.append(("description", description))
    if facebook_page_id:
        form_data.append(("facebook_page_id", facebook_page_id))
        
    for p in platforms:
        form_data.append(("platform[]", p))
        
    if additional_params:
        for k, v in additional_params.items():
            if isinstance(v, list):
                for item in v:
                    form_data.append((f"{k}[]", item))
            else:
                form_data.append((k, v))
                
    files = []
    opened_files = []
    try:
        for idx, photo_path in enumerate(photos):
            if not os.path.exists(photo_path):
                raise FileNotFoundError(f"Photo path does not exist locally: {photo_path}")
            import mimetypes
            mime_type, _ = mimetypes.guess_type(photo_path)
            mime_type = mime_type or "image/jpeg"
            f = open(photo_path, "rb")
            opened_files.append(f)
            files.append(("photos[]", (os.path.basename(photo_path), f, mime_type)))
            
        logger.info(f"Sending POST to {url} with fields {form_data} and {len(files)} files")
        response = requests.post(url, headers=headers, data=form_data, files=files, timeout=90)
        return handle_response(response)
    finally:
        # Crucial for resource/memory clean up! (SoC 3.5)
        for f in opened_files:
            try:
                f.close()
            except Exception:
                pass

def upload_text(api_key: str, user: str, platforms: list, title: str, description: str = None, facebook_page_id: str = None, additional_params: dict = None) -> dict:
    """
    Uploads a text-only post to various platforms via Upload-Post API.
    """
    url = "https://api.upload-post.com/api/upload_text"
    headers = {
        "Authorization": f"Apikey {api_key}"
    }
    
    form_data = []
    form_data.append(("user", user))
    form_data.append(("title", title))
    if description:
        form_data.append(("description", description))
    if facebook_page_id:
        form_data.append(("facebook_page_id", facebook_page_id))
        
    for p in platforms:
        form_data.append(("platform[]", p))
        
    if additional_params:
        for k, v in additional_params.items():
            if isinstance(v, list):
                for item in v:
                    form_data.append((f"{k}[]", item))
            else:
                form_data.append((k, v))
                
    logger.info(f"Sending POST to {url} with fields {form_data}")
    response = requests.post(url, headers=headers, data=form_data, timeout=60)
    return handle_response(response)

def upload_video(api_key: str, user: str, platforms: list, video_path: str, title: str = None, description: str = None, facebook_page_id: str = None, additional_params: dict = None) -> dict:
    """
    Uploads a video to various platforms via Upload-Post API.
    """
    url = "https://api.upload-post.com/api/upload"
    headers = {
        "Authorization": f"Apikey {api_key}"
    }
    
    form_data = []
    form_data.append(("user", user))
    if title:
        form_data.append(("title", title))
    if description:
        form_data.append(("description", description))
    if facebook_page_id:
        form_data.append(("facebook_page_id", facebook_page_id))
        
    for p in platforms:
        form_data.append(("platform[]", p))
        
    if additional_params:
        for k, v in additional_params.items():
            if isinstance(v, list):
                for item in v:
                    form_data.append((f"{k}[]", item))
            else:
                form_data.append((k, v))
                
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video path does not exist locally: {video_path}")
        
    import mimetypes
    mime_type, _ = mimetypes.guess_type(video_path)
    mime_type = mime_type or "video/mp4"
    
    logger.info(f"Sending POST to {url} with fields {form_data} and video file {video_path}")
    try:
        with open(video_path, "rb") as f:
            files = [("video", (os.path.basename(video_path), f, mime_type))]
            response = requests.post(url, headers=headers, data=form_data, files=files, timeout=120)
            return handle_response(response)
    except Exception as e:
        logger.error(f"Error during video upload: {e}")
        raise

def get_upload_status(api_key: str, request_id: str = None, job_id: str = None) -> dict:
    """
    Retrieve status of async upload or scheduled job.
    """
    url = "https://api.upload-post.com/api/uploadposts/status"
    headers = {
        "Authorization": f"Apikey {api_key}"
    }
    params = {}
    if request_id:
        params["request_id"] = request_id
    if job_id:
        params["job_id"] = job_id
        
    logger.info(f"Checking upload status at {url} with params {params}")
    response = requests.get(url, headers=headers, params=params, timeout=30)
    return handle_response(response)
