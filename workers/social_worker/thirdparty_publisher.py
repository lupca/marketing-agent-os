import logging
from core.ai_clients import upload_photos, upload_text, upload_video

logger = logging.getLogger("social_worker_thirdparty_publisher")

def publish_via_upload_post(api_key, user, platform, fb_page_id, title, is_video_post, photos) -> dict:
    logger.info(f"[publish_via_upload_post] Upload-Post API Publishing for platform={platform}")
    if is_video_post and photos:
        # Video publishing (Use the first media file as video)
        api_res = upload_video(
            api_key=api_key,
            user=user,
            platforms=[platform],
            video_path=photos[0],
            title=title,
            facebook_page_id=fb_page_id
        )
    elif photos:
        # Photos/Carousel publishing
        api_res = upload_photos(
            api_key=api_key,
            user=user,
            platforms=[platform],
            photos=photos,
            title=title,
            facebook_page_id=fb_page_id
        )
    else:
        # Text-only publishing
        api_res = upload_text(
            api_key=api_key,
            user=user,
            platforms=[platform],
            title=title,
            facebook_page_id=fb_page_id
        )
    return api_res
