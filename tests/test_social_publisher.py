# tests/test_social_publisher.py
import sys
import os
import uuid
import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from core.models import Workspace, MarketingCampaign, MasterContent, PlatformVariant, WorkspaceIntegration
from core.tasks import publish_to_social

class TestSocialPublisher(unittest.TestCase):
    
    def setUp(self):
        self.db: Session = SessionLocal()
        
    def tearDown(self):
        self.db.close()
        
    @patch("requests.post")
    def test_publish_facebook_page_variant(self, mock_post):
        """
        Creates a test variant for Facebook and publishes it synchronously
        using the publish_to_social Celery task.
        """
        print("\n=== STARTING SOCIAL PUBLISHER INTEGRATION TEST ===")
        
        # Mock requests.post response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "success", "post_id": "mock_fb_post_12345", "results": {"facebook": {"post_id": "mock_fb_post_12345"}}}
        mock_post.return_value = mock_resp
        
        # 1. Resolve workspace
        ws = self.db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        self.assertIsNotNone(ws, "Workspace Team Alpha Workspace not found!")
        ws_id = ws.id
        
        # Clean any existing mock integration configs to avoid duplicates
        self.db.query(WorkspaceIntegration).filter_by(workspace_id=ws_id, platform_name="upload-post").delete()
        self.db.commit()

        db_integration = WorkspaceIntegration(
            workspace_id=ws_id,
            platform_name="upload-post",
            config_key="api_key",
            config_value="mock_api_key_123",
            is_active=True
        )
        db_page_id = WorkspaceIntegration(
            workspace_id=ws_id,
            platform_name="upload-post",
            config_key="facebook_page_id",
            config_value="123456789",
            is_active=True
        )
        self.db.add(db_integration)
        self.db.add(db_page_id)
        self.db.commit()
        
        # 2. Resolve or create campaign
        campaign = self.db.query(MarketingCampaign).filter_by(workspace_id=ws_id).first()
        if not campaign:
            campaign = MarketingCampaign(
                workspace_id=ws_id,
                name="Chiến dịch Test Social Publisher",
                status="active",
                budget=50000.0
            )
            self.db.add(campaign)
            self.db.commit()
            self.db.refresh(campaign)
            
        # 3. Create MasterContent
        master = MasterContent(
            workspace_id=ws_id,
            campaign_id=campaign.id,
            core_message="Thông điệp Test Sáng Tạo",
            approval_status="approved"
        )
        self.db.add(master)
        self.db.commit()
        self.db.refresh(master)
        
        # 4. Create PlatformVariant for Facebook
        copy_text = "Đây là bài đăng test tự động từ hệ thống Marketing Agent OS - Quyết định Sếp duyệt lúc 2026-05-31."
        pv = PlatformVariant(
            workspace_id=ws_id,
            master_content_id=master.id,
            platform="facebook",
            adapted_copy=copy_text,
            publish_status="scheduled",
            content_type="text",
            meta_data={"test": True}
        )
        self.db.add(pv)
        self.db.commit()
        self.db.refresh(pv)
        
        print(f"Created PlatformVariant with ID: {pv.id}")
        
        # 5. Call publish_to_social Celery task synchronously
        try:
            # Call the task directly - Celery automatically handles 'bind=True'
            res = publish_to_social(str(pv.id))
            print("Publish Result:", res)
            
            # Verify status in database was updated
            self.db.refresh(pv)
            print(f"DB Status: {pv.publish_status}")
            print(f"DB Platform Post ID: {pv.platform_post_id}")
            print(f"DB Meta Data: {pv.meta_data}")
            
            self.assertEqual(pv.publish_status, "published")
            self.assertIsNotNone(pv.platform_post_id)
            
        except Exception as e:
            print("Publishing encountered an error:", e)
            self.fail(f"Integration test failed: {e}")
        finally:
            # Cleanup integrations, variant and master content
            self.db.query(WorkspaceIntegration).filter_by(workspace_id=ws_id, platform_name="upload-post").delete()
            self.db.delete(pv)
            self.db.delete(master)
            self.db.commit()

if __name__ == "__main__":
    unittest.main()
