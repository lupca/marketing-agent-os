# tests/test_social_publisher_refinements.py
import sys
import os
import uuid
import unittest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ai_clients.upload_post_client import upload_photos, UploadPostValidationError
from core.tasks import publish_to_social

class TestSocialPublisherRefinements(unittest.TestCase):
    
    @patch("requests.post")
    def test_dynamic_mime_type_guessing(self, mock_post):
        """Verify upload_photos dynamically detects MIME types based on file extension."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response
        
        # Create small temp files with png and mp4 extensions
        import tempfile
        fd1, path_png = tempfile.mkstemp(suffix=".png")
        fd2, path_mp4 = tempfile.mkstemp(suffix=".mp4")
        os.close(fd1)
        os.close(fd2)
        
        try:
            res = upload_photos(
                api_key="test-key",
                user="test-user",
                platforms=["instagram"],
                photos=[path_png, path_mp4],
                title="Test Dynamic Mime Type"
            )
            
            # Assert post was called
            self.assertTrue(mock_post.called)
            
            # Inspect the files parameter sent in requests.post
            call_kwargs = mock_post.call_args[1]
            files_sent = call_kwargs.get("files")
            self.assertIsNotNone(files_sent)
            self.assertEqual(len(files_sent), 2)
            
            # Verify mimetypes matched correctly
            self.assertEqual(files_sent[0][1][2], "image/png")
            self.assertEqual(files_sent[1][1][2], "video/mp4")
            print("MIME Type matching verified successfully: PNG -> image/png, MP4 -> video/mp4")
            
        finally:
            if os.path.exists(path_png): os.remove(path_png)
            if os.path.exists(path_mp4): os.remove(path_mp4)
            
    @patch("requests.post")
    def test_upload_video_mimetype_and_call(self, mock_post):
        """Verify upload_video dynamically detects MIME types and executes post."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response
        
        import tempfile
        fd, path_mp4 = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        
        try:
            from core.ai_clients.upload_post_client import upload_video
            res = upload_video(
                api_key="test-key",
                user="test-user",
                platforms=["tiktok"],
                video_path=path_mp4,
                title="Test Video Script Upload"
            )
            
            self.assertTrue(mock_post.called)
            call_kwargs = mock_post.call_args[1]
            files_sent = call_kwargs.get("files")
            self.assertIsNotNone(files_sent)
            self.assertEqual(len(files_sent), 1)
            self.assertEqual(files_sent[0][0], "video")
            self.assertEqual(files_sent[0][1][2], "video/mp4")
            print("upload_video MIME type and parameter formatting verified successfully.")
        finally:
            if os.path.exists(path_mp4):
                os.remove(path_mp4)
            
    def test_invalid_uuid_format_permanent_failure(self):
        """Verify malformed variant UUID format fails immediately with ValidationError without retry."""
        invalid_uuid = "malformed-uuid-format-12345"
        
        # Calling publish_to_social with invalid UUID should return status failed
        res = publish_to_social(invalid_uuid)
        self.assertEqual(res["status"], "failed")
        self.assertIn("Invalid variant_id UUID format", res["error"])
        print("ValueError to Permanent Failure conversion verified successfully for invalid UUID.")

    @patch("os.getenv")
    def test_missing_api_key_auth_error(self, mock_getenv):
        """Verify missing environment variable UPLOAD_POST_API_KEY triggers a permanent Auth error."""
        # Force getenv to return None for UPLOAD_POST_API_KEY
        mock_getenv.side_effect = lambda key: None if key == "UPLOAD_POST_API_KEY" else os.environ.get(key)
        
        # Set up valid UUID but not in DB
        valid_uuid = str(uuid.uuid4())
        
        # Test. The variant fetch will run. Let's mock DB query or use DB to seed a variant.
        # But wait! If the variant is not in the database, the task returns "Variant not found" before checking API Key.
        # So let's mock db query or insert a temporary variant.
        from db.connection import SessionLocal
        from core.models import Workspace, MarketingCampaign, MasterContent, PlatformVariant
        db = SessionLocal()
        try:
            ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
            self.assertIsNotNone(ws)
            ws_id = ws.id
            
            campaign = db.query(MarketingCampaign).filter_by(workspace_id=ws_id).first()
            if not campaign:
                campaign = MarketingCampaign(workspace_id=ws_id, name="Test Camp", budget=100.0)
                db.add(campaign)
                db.commit()
                
            master = MasterContent(workspace_id=ws_id, campaign_id=campaign.id, core_message="Test Msg")
            db.add(master)
            db.commit()
            
            pv = PlatformVariant(
                workspace_id=ws_id,
                master_content_id=master.id,
                platform="instagram",
                adapted_copy="Test copy",
                publish_status="scheduled"
            )
            db.add(pv)
            db.commit()
            
            # Now run task with missing API Key
            res = publish_to_social(str(pv.id))
            self.assertEqual(res["status"], "failed")
            self.assertIn("UPLOAD_POST_API_KEY is not configured", res["error"])
            
            # Verify DB was updated to 'failed'
            db.refresh(pv)
            self.assertEqual(pv.publish_status, "failed")
            self.assertIn("UPLOAD_POST_API_KEY is not configured", pv.meta_data.get("error_message", ""))
            print("Missing API Key triggers permanent AuthError verified successfully.")
            
            # Clean up
            db.delete(pv)
            db.delete(master)
            db.commit()
        finally:
            db.close()

if __name__ == "__main__":
    unittest.main()
