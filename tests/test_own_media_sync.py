import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import uuid

from db.connection import SessionLocal
from core.models import PlatformVariant, SocialInteraction, Workspace, MarketingCampaign, MasterContent
from core.tasks import sync_own_media_metrics

def test_sync_own_media_metrics_logic():
    db = SessionLocal()
    try:
        # Clear existing variants to avoid collision with mock data
        db.query(PlatformVariant).delete()
        db.commit()
        
        # 1. Setup Data
        ws = db.query(Workspace).first()
        camp = db.query(MarketingCampaign).first()
        if not camp:
            camp = MarketingCampaign(workspace_id=ws.id, name="Test Camp")
            db.add(camp)
            db.commit()
            
        master = db.query(MasterContent).first()
        if not master:
            master = MasterContent(workspace_id=ws.id, campaign_id=camp.id, core_message="Test")
            db.add(master)
            db.commit()
            
        variant = PlatformVariant(
            workspace_id=ws.id,
            master_content_id=master.id,
            platform="instagram",
            publish_status="published",
            platform_post_id="test_insta_12345",
            published_at=datetime.now(),
            metric_views=0,
            metric_likes=0
        )
        db.add(variant)
        db.commit()
        db.refresh(variant)

        # 2. Mock API Requests and Environment Variables
        with patch("requests.get") as mock_get, patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key: "mock_upload_post_api_key_123" if key == "UPLOAD_POST_API_KEY" else os.environ.get(key)
            def mock_get_side_effect(url, **kwargs):
                resp = MagicMock()
                resp.status_code = 200
                if "post-analytics" in url:
                    resp.json.return_value = {
                        "platforms": {
                            "instagram": {
                                "post_metrics": {
                                    "views": 2500,
                                    "likes": 340,
                                    "comments": 12,
                                    "shares": 50
                                }
                            }
                        }
                    }
                elif "comments" in url:
                    resp.json.return_value = {
                        "comments": [
                            {"id": "c1_test", "text": "Video hơi mờ và content quá chán, kịch bản lủng củng!"},
                            {"id": "c2_test", "text": "Sản phẩm tuyệt vời, mua ở đâu shop?"}
                        ]
                    }
                return resp
            
            mock_get.side_effect = mock_get_side_effect
            
            # 3. Execute Job
            result = sync_own_media_metrics()
            
            # 4. Assertions
            assert result["status"] == "success"
            
            db.refresh(variant)
            assert variant.metric_views == 2500
            assert variant.metric_likes == 340
            assert variant.metric_comments == 12
            
            # Check if comments were saved correctly
            interactions = db.query(SocialInteraction).filter_by(variant_id=variant.id).all()
            assert len(interactions) >= 2
            
            # Find the negative one
            negative = [i for i in interactions if i.sentiment == 'negative' and i.platform_user_id == "c1_test"]
            assert len(negative) == 1
            assert "chán" in negative[0].content
            
    finally:
        db.close()
