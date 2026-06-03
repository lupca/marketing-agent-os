# tests/test_workflow.py
import os
import sys
import uuid
import unittest
from sqlalchemy.orm import Session

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from core import pipeline_tracker
from core.models import (
    Workspace, ProductService, MarketingCampaign,
    PlatformVariant, AdMapper, AIInsightPending, RAGChunk,
    SocialAccount, CampaignSocialAccount
)
from core.bandit_orchestrator import compute_mab_beliefs, trigger_autonomous_generation
from tests.mock_ollama import LocalOllamaTestCase

class TestAutonomousCreativeEngine(LocalOllamaTestCase):
    
    def setUp(self):
        super().setUp()
        self.db = SessionLocal()
        
        # Explicitly set execution mode to live for workflow tests to trigger publisher DB writes
        pipeline_tracker.set_execution_mode("live")
        
        # Verify that the database is already seeded with "TOPVNSPORT Workspace"
        self.ws = self.db.query(Workspace).filter_by(name="TOPVNSPORT Workspace").first()
        if not self.ws:
            # Fallback mock setup if DB seeding ran out of context
            self.ws = Workspace(
                id=uuid.uuid4(),
                name="TOPVNSPORT Workspace",
                settings={}
            )
            self.db.add(self.ws)
            self.db.commit()
            
        self.prod = self.db.query(ProductService).filter_by(workspace_id=self.ws.id).first()
        if not self.prod:
            # Mock brand identity
            from core.models import BrandIdentity
            brand = BrandIdentity(
                id=uuid.uuid4(),
                workspace_id=self.ws.id,
                brand_name="TOPVNSPORT (TOPVNSPORT)",
                voice_and_tone="Duy trì một giọng điệu truyền thông chuyên gia thân thiện.",
                dos_and_donts={"dos": ["hàng chính hãng"], "donts": ["hàng giả"]}
            )
            self.db.add(brand)
            self.db.commit()
            
            self.prod = ProductService(
                id=uuid.uuid4(),
                workspace_id=self.ws.id,
                brand_id=brand.id,
                name="Vợt cầu lông TOPVNSPORT V200i",
                description="Đũa dẻo trợ lực tối đa",
                usp="Khung sợi carbon chịu sức căng cao"
            )
            self.db.add(self.prod)
            self.db.commit()

        # Create a new active campaign to run MAB on
        self.camp = MarketingCampaign(
            id=uuid.uuid4(),
            workspace_id=self.ws.id,
            product_id=self.prod.id,
            name=f"Chiến dịch Test Tự Trị {uuid.uuid4().hex[:6]}",
            campaign_type="LEAD_GEN",
            status="active",
            budget=5000000.0
        )
        self.db.add(self.camp)
        self.db.commit()
        
    def tearDown(self):
        # Restore default shadow mode
        pipeline_tracker.set_execution_mode("shadow")
        
        # Clean up campaign and generated variants
        self.db.query(AdMapper).delete()
        self.db.query(PlatformVariant).filter_by(workspace_id=self.ws.id).delete()
        self.db.query(AIInsightPending).filter_by(workspace_id=self.ws.id).delete()
        self.db.query(MarketingCampaign).filter_by(id=self.camp.id).delete()
        self.db.commit()
        self.db.close()
        super().tearDown()
        
    def test_mab_cold_start_math(self):
        """Verify that the MAB computes priors and baseline metrics during Cold Start using SQL."""
        print("\n[START COLD START MAB MATH TEST]")
        
        mab_res = compute_mab_beliefs(self.db, str(self.camp.id), "LEAD_GEN")
        
        self.assertTrue(mab_res["cold_start"])
        self.assertIn("beliefs", mab_res)
        self.assertIn("metrics", mab_res)
        
        # All 6 angles should receive a baseline priority distribution weight
        beliefs = mab_res["beliefs"]
        self.assertEqual(len(beliefs), 6)
        self.assertAlmostEqual(sum(beliefs.values()), 1.0)
        
        print(" -> Cold-start SQL calculations validated successfully!")
        
    def test_stateless_execution_pipeline(self):
        """Simulate the uninterrupted, stateless creative generation execution loop."""
        print(f"\n[START STATELESS EXECUTION PIPELINE TEST] Campaign ID: {self.camp.id}")
        
        # Verify database starts with 0 variants for this run
        var_count_before = self.db.query(PlatformVariant).filter_by(workspace_id=self.ws.id).count()
        self.assertEqual(var_count_before, 0)
        
        # Execute the stateless pipeline
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        task = trigger_autonomous_generation(
            workspace_id=str(self.ws.id),
            campaign_id=str(self.camp.id),
            product_id=str(self.prod.id),
            db=self.db
        )
        result_state = loop.run_until_complete(task)
        
        # Verify graph completed fully
        self.assertEqual(result_state["sop_stage"], "completed")
        self.assertTrue(len(result_state["generated_variants"]) > 0)
        
        # 1. Verify variants were persisted in PostgreSQL
        var_count_after = self.db.query(PlatformVariant).filter_by(workspace_id=self.ws.id).count()
        self.assertTrue(var_count_after > 0)
        
        # 2. Verify AdMapper mapped variant IDs to external platform Ad IDs
        mapped_entries = self.db.query(AdMapper).count()
        self.assertTrue(mapped_entries > 0)
        
        # 3. Verify AI post-mortem explanation is registered in ai_insights_pending table
        pending_insights = self.db.query(AIInsightPending).filter_by(workspace_id=self.ws.id).count()
        self.assertTrue(pending_insights > 0)
        
        # 4. Verify context was fetched without hallucination
        saved_var = self.db.query(PlatformVariant).filter_by(workspace_id=self.ws.id).first()
        self.assertIsNotNone(saved_var)
        self.assertIn("facebook", saved_var.platform)
        
        print(" -> Uninterrupted stateless execution pipeline ran to completion successfully!")
        print(" -> Database variant persistency, AdMapper indexing, and Pending Insights validated successfully!")

    def test_omnichannel_platform_specific_generation(self):
        """Verify that the pipeline generates, validates, and publishes mixed platform variants (Facebook text and TikTok video scripts)."""
        print(f"\n[START OMNICHANNEL PLATFORM SPECIFIC GENERATION TEST] Campaign ID: {self.camp.id}")
        
        # 1. Create a Facebook social account and link it
        fb_acc = SocialAccount(
            id=uuid.uuid4(),
            workspace_id=self.ws.id,
            platform="facebook",
            account_name="Test Facebook Page",
            account_id="fake_fb_account_id_123",
            access_token="fake_token",
            status="active"
        )
        self.db.add(fb_acc)
        
        # 2. Create a TikTok social account and link it
        tt_acc = SocialAccount(
            id=uuid.uuid4(),
            workspace_id=self.ws.id,
            platform="tiktok",
            account_name="Test TikTok Account",
            account_id="fake_tt_account_id_123",
            access_token="fake_token",
            status="active"
        )
        self.db.add(tt_acc)
        self.db.commit()
        
        # 3. Create campaign many-to-many links
        link_fb = CampaignSocialAccount(
            id=uuid.uuid4(),
            campaign_id=self.camp.id,
            social_account_id=fb_acc.id
        )
        link_tt = CampaignSocialAccount(
            id=uuid.uuid4(),
            campaign_id=self.camp.id,
            social_account_id=tt_acc.id
        )
        self.db.add(link_fb)
        self.db.add(link_tt)
        self.db.commit()
        
        # Verify links exist
        links = self.db.query(CampaignSocialAccount).filter_by(campaign_id=self.camp.id).all()
        self.assertEqual(len(links), 2)
        
        # 4. Execute the stateless pipeline
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        task = trigger_autonomous_generation(
            workspace_id=str(self.ws.id),
            campaign_id=str(self.camp.id),
            product_id=str(self.prod.id),
            db=self.db
        )
        result_state = loop.run_until_complete(task)
        
        # Verify graph completed fully
        self.assertEqual(result_state["sop_stage"], "completed")
        variants = result_state["generated_variants"]
        self.assertTrue(len(variants) > 0)
        
        # Verify we generated variants for BOTH platforms
        platforms = [v.get("platform") for v in variants]
        self.assertIn("facebook", platforms)
        self.assertIn("tiktok", platforms)
        
        # Verify content type and format logic
        for v in variants:
            platform = v.get("platform")
            content_type = v.get("content_type")
            copy = v.get("adapted_copy", "")
            
            if platform == "tiktok":
                self.assertEqual(content_type, "video_script")
                # TikTok video script should be structured with Visual/Audio or contain cues
                self.assertTrue(("[Visual" in copy or "[Audio" in copy) or "Visual" in copy)
            else:
                self.assertEqual(platform, "facebook")
                self.assertEqual(content_type, "text")
                # Facebook variant should be regular text
                self.assertNotIn("[Visual]", copy)
                
        # 5. Verify database PlatformVariant records contain the correct content_type
        db_variants = self.db.query(PlatformVariant).filter_by(workspace_id=self.ws.id).all()
        self.assertTrue(len(db_variants) > 0)
        
        tiktok_db_vars = [pv for pv in db_variants if pv.platform == "tiktok"]
        fb_db_vars = [pv for pv in db_variants if pv.platform == "facebook"]
        
        self.assertTrue(len(tiktok_db_vars) > 0)
        self.assertTrue(len(fb_db_vars) > 0)
        
        for pv in tiktok_db_vars:
            self.assertEqual(pv.content_type, "video_script")
        for pv in fb_db_vars:
            self.assertEqual(pv.content_type, "text")
            
        print(" -> Mixed Facebook text and TikTok video script generation completely verified!")
        
        # Clean up accounts and campaign links
        self.db.query(CampaignSocialAccount).filter_by(campaign_id=self.camp.id).delete()
        self.db.delete(fb_acc)
        self.db.delete(tt_acc)
        self.db.commit()

if __name__ == "__main__":
    unittest.main()
