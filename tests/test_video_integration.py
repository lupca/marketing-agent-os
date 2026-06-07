# tests/test_video_integration.py
import os
import sys
import uuid
import unittest
from unittest.mock import patch, MagicMock
from requests.exceptions import HTTPError

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from core.models import Workspace, ProductService, MarketingCampaign, PlatformVariant, BrandIdentity, MasterContent, MediaAsset
from core.integrations.video_client import submit_video_job, get_job_status
from workers.video_worker.tasks import poll_video_agent_jobs
from graphs.autonomous.publisher import publisher_node
from core import pipeline_tracker

class TestVideoIntegration(unittest.TestCase):
    
    def setUp(self):
        super().setUp()
        self.db = SessionLocal()
        pipeline_tracker.set_execution_mode("live")
        
        # Setup mock test data
        self.ws_id = uuid.uuid4()
        self.camp_id = uuid.uuid4()
        self.workspace_name = f"Antigravity Test Workspace {self.ws_id.hex[:8]}"
        
        # Clean up any existing conflicting records
        self._cleanup_db()
        
        # Create and commit workspace first to guarantee foreign key integrity
        self.workspace = Workspace(
            id=self.ws_id,
            name=self.workspace_name,
            settings={}
        )
        self.db.add(self.workspace)
        self.db.commit()
        
        # Create brand
        self.brand = BrandIdentity(
            workspace_id=self.ws_id,
            brand_name="Antigravity Test Brand",
            voice_and_tone="Innovative and direct"
        )
        # Create campaign
        self.campaign = MarketingCampaign(
            id=self.camp_id,
            workspace_id=self.ws_id,
            name="Video Integration Campaign",
            status="active"
        )
        self.db.add(self.brand)
        self.db.add(self.campaign)
        self.db.commit()

    def tearDown(self):
        pipeline_tracker.set_execution_mode("shadow")
        self._cleanup_db()
        self.db.close()
        super().tearDown()

    def _cleanup_db(self):
        # Delete dependent tables first, then parent workspace
        self.db.query(PlatformVariant).filter(PlatformVariant.workspace_id == self.ws_id).delete()
        self.db.query(BrandIdentity).filter(BrandIdentity.workspace_id == self.ws_id).delete()
        self.db.query(MediaAsset).filter(MediaAsset.workspace_id == self.ws_id).delete()
        self.db.query(MasterContent).filter(MasterContent.workspace_id == self.ws_id).delete()
        self.db.query(MarketingCampaign).filter(MarketingCampaign.workspace_id == self.ws_id).delete()
        self.db.query(Workspace).filter(Workspace.id == self.ws_id).delete()
        self.db.commit()

    # =====================================================================
    # 1. UNIT TESTS: HTTP API CLIENT (using standard Mock)
    # =====================================================================

    @patch("core.integrations.video_client.requests.post")
    def test_submit_video_job_http_201_success(self, mock_post):
        """Verify submitting video job successfully builds and sends TMCP payload."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 888, "status": "PENDING"}
        mock_post.return_value = mock_resp

        result = submit_video_job(
            variant_id="var_video_001",
            video_script="Kịch bản video AI tự động",
            platform="tiktok",
            workspace_id=str(self.ws_id),
            campaign_id=str(self.camp_id),
            brand_name="Test Brand",
            brand_voice="Energetic",
            campaign_name="Test Campaign",
            campaign_objective="LEAD_GEN",
            angle_name="Uniqueness"
        )

        self.assertEqual(result["job_id"], 888)
        self.assertEqual(result["status"], "PENDING")

        # Verify request structure and headers
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        
        headers = call_kwargs["headers"]
        payload = call_kwargs["json"]
        
        self.assertEqual(headers.get("X-TMCP-Key"), "tmcp_secret_key_123")
        self.assertEqual(payload["source_id"], "var_video_001")
        self.assertEqual(payload["brand_context"]["brand_name"], "Test Brand")
        self.assertEqual(payload["brand_context"]["tone_of_voice"], "Energetic")
        self.assertEqual(payload["campaign_context"]["campaign_name"], "Test Campaign")
        self.assertEqual(payload["campaign_context"]["objective"], "LEAD_GEN")
        self.assertEqual(payload["variant_data"]["script_content"], "Kịch bản video AI tự động")
        self.assertEqual(payload["content_brief_context"]["angle_name"], "Uniqueness")

    @patch("core.integrations.video_client.requests.post")
    def test_submit_video_job_http_403_forbidden(self, mock_post):
        """Verify client correctly throws HTTPError when unauthorized."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        response_error = HTTPError("403 Forbidden")
        response_error.response = mock_resp
        mock_resp.raise_for_status.side_effect = response_error
        mock_post.return_value = mock_resp

        with self.assertRaises(HTTPError):
            submit_video_job(
                variant_id="var_video_001",
                video_script="Kịch bản video AI tự động",
                platform="tiktok",
                workspace_id=str(self.ws_id),
                campaign_id=str(self.camp_id)
            )

    @patch("core.integrations.video_client.requests.get")
    def test_get_job_status_completed(self, mock_get):
        """Verify client parses completed video job response correctly."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "COMPLETED",
            "result_url": "s3://video-output/job_888/final.mp4",
            "progress_percent": 100
        }
        mock_get.return_value = mock_resp

        status = get_job_status(888)
        self.assertEqual(status["status"], "COMPLETED")
        self.assertEqual(status["result_url"], "s3://video-output/job_888/final.mp4")
        self.assertEqual(status["progress"], 100)
        self.assertIsNone(status["error"])

    # =====================================================================
    # 2. COMPONENT TESTS: PUBLISHER NODE DELEGATION
    # =====================================================================

    @patch("core.integrations.video_client.submit_video_job")
    @patch("core.integrations.fb_client.init_facebook_client")
    def test_publisher_node_video_delegation(self, mock_init_fb, mock_submit_video):
        """Verify publisher_node routes video script to Video Agent and sets database states."""
        mock_submit_video.return_value = {"job_id": 555, "status": "PENDING"}
        mock_init_fb.return_value = (MagicMock(), "mock_fb_acc_id", False)

        video_var_id = str(uuid.uuid4())
        text_var_id = str(uuid.uuid4())

        state = {
            "workspace_id": str(self.ws_id),
            "campaign_id": str(self.camp_id),
            "campaign_objective": "LEAD_GEN",
            "generated_variants": [
                {
                    "id": video_var_id,
                    "variant_id": video_var_id,
                    "content_type": "video_script",
                    "platform": "tiktok",
                    "adapted_copy": "Custom visual and visual narration script for TikTok ads.",
                    "angle_name": "FOMO"
                },
                {
                    "id": text_var_id,
                    "variant_id": text_var_id,
                    "content_type": "text",
                    "platform": "facebook",
                    "adapted_copy": "Facebook text only copy post."
                }
            ]
        }

        # Run Publisher Node with Exception Capturing
        try:
            result_state = publisher_node(state)
            print("--> PUBLISHER NODE FINISHED. RETURNED STATE:", result_state)
        except Exception as e:
            print("--> PUBLISHER NODE THREW AN EXCEPTION:")
            import traceback
            traceback.print_exc()
            raise e

        # Assertions
        # Video client should be called with correct campaign, brand, and angle contexts
        mock_submit_video.assert_called_once_with(
            variant_id=video_var_id,
            video_script="Custom visual and visual narration script for TikTok ads.",
            platform="tiktok",
            workspace_id=str(self.ws_id),
            campaign_id=str(self.camp_id),
            brand_name="Antigravity Test Brand",
            brand_voice="Innovative and direct",
            campaign_name="Video Integration Campaign",
            campaign_objective="LEAD_GEN",
            angle_name="FOMO"
        )

        # Check DB states
        variants_in_db = self.db.query(PlatformVariant).filter_by(workspace_id=self.ws_id).all()
        self.assertEqual(len(variants_in_db), 2)
        
        tiktok_var = next(v for v in variants_in_db if v.platform == "tiktok")
        fb_var = next(v for v in variants_in_db if v.platform == "facebook")

        self.assertEqual(tiktok_var.publish_status, "generating_media")
        self.assertEqual(tiktok_var.meta_data["video_agent_job_id"], 555)

        self.assertEqual(fb_var.publish_status, "shadow" if pipeline_tracker.get_execution_mode() == "shadow" else "published")

    # =====================================================================
    # 3. COMPONENT TESTS: CELERY POLLING TASK
    # =====================================================================

    @patch("workers.video_worker.tasks.get_job_status")
    @patch("workers.video_worker.tasks.celery_app.send_task")
    def test_poll_video_agent_jobs_completed_trigger(self, mock_send_task, mock_get_status):
        """Verify polling task processes COMPLETED video jobs and triggers publish_to_social."""
        # Create MasterContent first to satisfy ForeignKey constraint
        test_mc = MasterContent(
            id=uuid.uuid4(),
            workspace_id=self.ws_id,
            campaign_id=self.camp_id,
            core_message="Test Master Content for Polling Task",
            approval_status="approved"
        )
        self.db.add(test_mc)
        self.db.commit()

        # Seed variant waiting for video
        v_id = uuid.uuid4()
        test_var = PlatformVariant(
            id=v_id,
            workspace_id=self.ws_id,
            master_content_id=test_mc.id,
            platform="tiktok",
            content_type="video_script",
            publish_status="generating_media",
            meta_data={"video_agent_job_id": 999}
        )
        self.db.add(test_var)
        self.db.commit()

        # Mock API returns COMPLETED
        mock_get_status.return_value = {
            "status": "COMPLETED",
            "result_url": "s3://video-output/rendering_999.mp4",
            "progress": 100,
            "error": None
        }

        # Execute Polling Task
        poll_video_agent_jobs()

        # Verify DB is updated
        self.db.refresh(test_var)
        self.assertEqual(test_var.publish_status, "ready_to_publish")
        
        # Verify that platform_media_ids now contains a UUID reference instead of URL string
        self.assertEqual(len(test_var.platform_media_ids), 1)
        self.assertIsInstance(test_var.platform_media_ids[0], uuid.UUID)
        
        # Verify MediaAsset was created
        media_asset = self.db.query(MediaAsset).filter_by(id=test_var.platform_media_ids[0]).first()
        self.assertIsNotNone(media_asset)
        self.assertEqual(media_asset.file_url, "s3://video-output/rendering_999.mp4")
        self.assertEqual(media_asset.file_key, "rendering_999.mp4")

        # Verify social publishing task was triggered
        mock_send_task.assert_called_once_with(
            "workers.social_worker.tasks.publish_to_social",
            args=[str(v_id)],
            queue="social_publisher"
        )

    @patch("workers.video_worker.tasks.get_job_status")
    @patch("workers.video_worker.tasks.celery_app.send_task")
    def test_poll_video_agent_jobs_failed(self, mock_send_task, mock_get_status):
        """Verify polling task handles failed video jobs and saves error reason."""
        # Create MasterContent first to satisfy ForeignKey constraint
        test_mc = MasterContent(
            id=uuid.uuid4(),
            workspace_id=self.ws_id,
            campaign_id=self.camp_id,
            core_message="Test Master Content for Polling Task Failure",
            approval_status="approved"
        )
        self.db.add(test_mc)
        self.db.commit()

        # Seed variant waiting for video
        v_id = uuid.uuid4()
        test_var = PlatformVariant(
            id=v_id,
            workspace_id=self.ws_id,
            master_content_id=test_mc.id,
            platform="tiktok",
            content_type="video_script",
            publish_status="generating_media",
            meta_data={"video_agent_job_id": 999}
        )
        self.db.add(test_var)
        self.db.commit()

        # Mock API returns FAILED
        mock_get_status.return_value = {
            "status": "FAILED",
            "result_url": None,
            "progress": 50,
            "error": "Timeout during rendering in Worker Render"
        }

        # Execute Polling Task
        poll_video_agent_jobs()

        # Verify DB is updated
        self.db.refresh(test_var)
        self.assertEqual(test_var.publish_status, "video_generation_failed")
        self.assertEqual(test_var.meta_data["video_error"], "Timeout during rendering in Worker Render")

        # Verify social publishing task was NOT triggered
        mock_send_task.assert_not_called()

if __name__ == "__main__":
    unittest.main()
