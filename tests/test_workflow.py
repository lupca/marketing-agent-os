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
                brand_name="TOPVNSPORT",
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
        
        # Seed a mock Facebook social account for the workspace
        from core.models import SocialAccount
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
        
        # Seed WorkspaceIntegration with a mock facebook_page_id to satisfy publisher validation
        from core.models import WorkspaceIntegration
        integration = WorkspaceIntegration(
            id=uuid.uuid4(),
            workspace_id=self.ws.id,
            platform_name="upload-post",
            config_key="facebook_page_id",
            config_value="61580803074671",
            is_active=True
        )
        self.db.add(integration)
        self.db.commit()
        
    def tearDown(self):
        # Restore default shadow mode
        pipeline_tracker.set_execution_mode("shadow")
        
        # Clean up campaign and generated variants
        self.db.query(AdMapper).delete()
        self.db.query(PlatformVariant).filter_by(workspace_id=self.ws.id).delete()
        self.db.query(AIInsightPending).filter_by(workspace_id=self.ws.id).delete()
        
        # Avoid database state leakage across test runs
        from core.models import WorkspaceIntegration, SocialAccount, CampaignSocialAccount
        self.db.query(CampaignSocialAccount).filter(CampaignSocialAccount.campaign_id == self.camp.id).delete()
        self.db.query(SocialAccount).filter_by(workspace_id=self.ws.id).delete()
        self.db.query(WorkspaceIntegration).filter_by(workspace_id=self.ws.id).delete()
        
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

    def test_mab_baseline_copy_iteration(self):
        """Verify that the MAB orchestrator extracts the best performing baseline variant copy and passes it to the generation node."""
        print(f"\n[START MAB BASELINE COPY ITERATION TEST] Campaign ID: {self.camp.id}")
        from core.models import CampaignAnalytics, MasterContent
        
        # 1. Seed a CampaignAnalytics record so that it is not a Cold Start
        analytics = CampaignAnalytics(
            id=uuid.uuid4(),
            campaign_id=self.camp.id,
            platform="facebook",
            impressions=1000,
            clicks=100,
            conversions=10,
            spend=100000.0,
            cpc=1000.0,
            cpa=10000.0,
            cpm=100000.0,
            ctr=0.1000
        )
        self.db.add(analytics)
        self.db.commit()
        
        # 2. Determine which exploit angle is calculated based on hash of analytics.id
        from core.bandit_orchestrator import compute_mab_beliefs
        mab_res = compute_mab_beliefs(self.db, str(self.camp.id), "LEAD_GEN")
        priors = mab_res["beliefs"]
        best_angle = max(priors, key=priors.get)
        self.assertFalse(mab_res["cold_start"])
        
        # 3. Create a MasterContent and a PlatformVariant with this exploit angle
        master = MasterContent(
            id=uuid.uuid4(),
            workspace_id=self.ws.id,
            campaign_id=self.camp.id,
            core_message="Baseline Master Content Copy",
            approval_status="approved"
        )
        self.db.add(master)
        self.db.commit()
        
        baseline_text = "Nội dung quảng cáo V1 xuất sắc nhất hệ mặt trời!"
        variant = PlatformVariant(
            id=uuid.uuid4(),
            workspace_id=self.ws.id,
            master_content_id=master.id,
            platform="facebook",
            adapted_copy=baseline_text,
            publish_status="published",
            content_type="text",
            meta_data={"angle_name": best_angle},
            metric_views=100,
            metric_likes=10
        )
        self.db.add(variant)
        self.db.commit()
        
        # 4. Patch generate_platform_variant or generate_text to capture the baseline_copy parameter
        from unittest.mock import patch
        
        captured_baselines = []
        original_generate_platform_variant = sys.modules["graphs.autonomous.generation"].generate_platform_variant
        
        def spy_generate_platform_variant(*args, **kwargs):
            # Capture baseline_copy
            captured_baselines.append(kwargs.get("baseline_copy"))
            return original_generate_platform_variant(*args, **kwargs)
            
        with patch("graphs.autonomous.generation.generate_platform_variant", side_effect=spy_generate_platform_variant):
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
            
        # 5. Assertions
        # Check that baseline_copy was correctly loaded into the state
        self.assertEqual(result_state["baseline_copy"], baseline_text)
        
        # Check that baseline_copy was passed to generate_platform_variant at least once (for the exploit angle)
        self.assertIn(baseline_text, captured_baselines)
        
        print(" -> MAB baseline copy iteration successfully verified!")
        
        # Clean up
        self.db.delete(master)
        self.db.delete(analytics)
        self.db.commit()

if __name__ == "__main__":
    unittest.main()
