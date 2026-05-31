# tests/test_market_intelligence.py
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import uuid
from sqlalchemy.orm import Session

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from db.seed import seed_database
from core.models import Workspace, ProductService, RAGDocument, RAGChunk, AgentDecision
from core.ai_clients.serpapi_client import search_youtube, get_youtube_transcript, get_youtube_comments
from core.market_intelligence import fetch_and_process_market_data
from core.tasks import radar_market_first_cron

class TestMarketIntelligence(unittest.TestCase):
    
    def setUp(self):
        self.db: Session = SessionLocal()
        seed_database(self.db)
        self.workspace = self.db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        self.assertIsNotNone(self.workspace)
        self.workspace_id = str(self.workspace.id)
        # Clear existing workspace documents to prevent duplicate file hash collision during tests
        self.db.query(RAGDocument).filter_by(workspace_id=uuid.UUID(self.workspace_id)).delete()
        self.db.commit()
        
    def tearDown(self):
        self.db.close()
        
    @patch("core.ai_clients.serpapi_client.get_serpapi_key")
    def test_serpapi_client_fallback(self, mock_get_key):
        """Verify that SerpApi client works correctly and yields mock fallbacks when API keys are empty."""
        mock_get_key.return_value = ""
        res_search = search_youtube("G-Agent Tech", self.workspace_id)
        self.assertIn("video_results", res_search)
        self.assertTrue(len(res_search["video_results"]) > 0)
        self.assertEqual(res_search["video_results"][0]["video_id"], "mockvid0001")
        
        res_trans = get_youtube_transcript("mockvid0001", self.workspace_id)
        self.assertIn("transcript", res_trans)
        self.assertTrue(len(res_trans["transcript"]) > 0)
        self.assertIn("chi phí chuyển đổi", res_trans["transcript"][0]["snippet"])

        res_comments = get_youtube_comments("mockvid0001", self.workspace_id)
        self.assertIn("comments", res_comments)
        self.assertTrue(len(res_comments["comments"]) > 0)
        self.assertEqual(res_comments["comments"][0]["author"], "Hải Nam")

    @patch("core.market_intelligence.upload_file")
    @patch("core.market_intelligence.generate_text")
    @patch("core.market_intelligence.search_youtube")
    @patch("core.market_intelligence.get_youtube_transcript")
    @patch("core.market_intelligence.get_youtube_comments")
    def test_fetch_and_process_market_data(self, mock_comments, mock_trans, mock_search, mock_generate, mock_upload):
        """Verify that fetching and processing YouTube competitor data successfully uploads raw JSON and stores analysis in RAG."""
        mock_search.return_value = {
            "video_results": [
                {
                    "title": "Hướng dẫn tối ưu CPA quảng cáo đột phá",
                    "link": "https://www.youtube.com/watch?v=mockvid0001",
                    "video_id": "mockvid0001",
                    "channel": {"name": "Học Viện Marketing Tech"},
                    "description": "Video chia sẻ bí quyết viết kịch bản."
                }
            ]
        }
        mock_trans.return_value = {"transcript": [{"snippet": "chi phí chuyển đổi"}]}
        mock_comments.return_value = {"comments": [{"author": "Hải Nam", "text": "hay"}]}
        
        # 1. Mock generate_text to return valid JSON analysis report
        mock_generate.return_value = """
        {
          "is_trash": false,
          "hook": "Giải pháp AI đột phá giảm 50% CPA",
          "hook_type": "nêu giải pháp",
          "sentiment": {
            "positive_pct": 80,
            "neutral_pct": 10,
            "negative_pct": 10
          },
          "pain_points": ["CPA tăng quá cao", "Duyệt kịch bản thủ công mất thời gian"],
          "markdown_report": "# Báo cáo phân tích đối thủ\\nHook rất hay đánh trúng nỗi sợ của CMO."
        }
        """
        
        # 2. Cleanup existing market intel docs for workspace to avoid hash duplicate triggers
        self.db.query(RAGDocument).filter_by(workspace_id=uuid.UUID(self.workspace_id), file_name="market_intel_youtube_mockvid0001.md").delete()
        self.db.commit()
        
        # 3. Call pipeline
        processed = fetch_and_process_market_data(self.db, self.workspace_id, "G-Agent Tech", limit=1)
        
        # 4. Verify outputs
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]["video_id"], "mockvid0001")
        self.assertEqual(processed[0]["analysis"]["hook_type"], "nêu giải pháp")
        
        # Verify S3 upload was triggered
        self.assertTrue(mock_upload.called)
        
        # Verify document was inserted into RAG database with tags and metadata
        doc = self.db.query(RAGDocument).filter_by(
            workspace_id=uuid.UUID(self.workspace_id), 
            file_name="market_intel_youtube_mockvid0001.md"
        ).first()
        self.assertIsNotNone(doc)
        self.assertIn("market_intel", doc.access_tags)
        self.assertEqual(doc.meta_data.get("hook"), "Giải pháp AI đột phá giảm 50% CPA")
        
    @patch("core.tasks.generate_text")
    @patch("core.tasks.search_youtube")
    def test_radar_market_first_cron(self, mock_search, mock_generate):
        """Verify that the daily radar cron job successfully scans competitor channels, triggers alerts and logs decisions."""
        mock_search.return_value = {
            "video_results": [
                {
                    "title": "Xu hướng TikTok Ads 2026",
                    "link": "https://youtube.com/tiktokads",
                    "video_id": "tiktokads123",
                    "channel": {"name": "TikTok Master"},
                    "description": "Video thảo luận về cách phân bổ ngân sách và tối ưu CPA Tiktok."
                }
            ]
        }
        
        mock_generate.return_value = """
        {
          "has_trend": true,
          "trend_description": "Khách hàng dịch chuyển mạnh sang Tiktok Ads tự trị",
          "matching_product": "Marketing Agent OS Software",
          "cmo_alert_message": "Phát hiện xu hướng Tiktok Ads tự trị tăng mạnh. Khuyên sếp triển khai kịch bản TikTok sớm."
        }
        """
        
        # Count existing alerts
        initial_alerts_count = self.db.query(AgentDecision).filter_by(
            workspace_id=uuid.UUID(self.workspace_id),
            agent_name="Market Radar Agent",
            decision_status="alert"
        ).count()
        
        # Call cron task
        res = radar_market_first_cron()
        self.assertEqual(res["status"], "success")
        
        # Verify alert was logged in database
        final_alerts = self.db.query(AgentDecision).filter_by(
            workspace_id=uuid.UUID(self.workspace_id),
            agent_name="Market Radar Agent",
            decision_status="alert"
        ).all()
        
        self.assertEqual(len(final_alerts), initial_alerts_count + 1)
        self.assertIn("Phát hiện xu hướng Tiktok Ads tự trị tăng mạnh", final_alerts[-1].reason)

if __name__ == "__main__":
    unittest.main()
