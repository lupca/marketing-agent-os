# tests/test_fb_client.py
import unittest
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from core.dependencies import get_session
from core.models import SocialAccount, AdMapper, PlatformVariant, CampaignSocialAccount
from core.integrations.fb_client import (
    get_fb_client,
    fetch_campaign_metrics,
    FacebookAccountDisabledError,
    init_facebook_client,
    batch_create_creatives,
    batch_create_ads
)
from core.db_services import save_publisher_state
from facebook_business.exceptions import FacebookRequestError

class TestFacebookClientIntegration(unittest.TestCase):

    def setUp(self):
        # Establish database session for seeding mock test data
        with get_session() as db:
            self.db = db
            self.workspace_id = uuid.uuid4()
            
            # Create a dedicated test workspace to avoid interfering with real data
            from core.models import Workspace
            self.test_ws = Workspace(id=self.workspace_id, name=f"Test FB Workspace {self.workspace_id}")
            db.add(self.test_ws)
            db.commit()

    def tearDown(self):
        with get_session() as db:
            from core.models import Workspace
            db.query(Workspace).filter_by(id=self.workspace_id).delete()
            db.commit()

    def test_get_fb_client_success(self):
        """Verify get_fb_client initializes Facebook SDK successfully with valid credentials."""
        with get_session() as db:
            # Create a mock social account with active credentials
            social = SocialAccount(
                workspace_id=self.workspace_id,
                platform="facebook",
                account_name="Test FB Account",
                account_id="act_12345678",
                app_id="1726784475006075",
                app_secret="df47841a6e5f71043fa71863f8454775",
                access_token="test_token_123",
                status="active"
            )
            db.add(social)
            db.commit()
            db.refresh(social)

            with patch("core.integrations.fb_client.FacebookAdsApi") as mock_api:
                mock_api_instance = MagicMock()
                mock_api.init.return_value = mock_api_instance
                mock_api.get_default_api.return_value = mock_api_instance
                
                api, account_id = get_fb_client(str(self.workspace_id), db)
                
                mock_api.init.assert_called_once_with(
                    app_id="1726784475006075",
                    app_secret="df47841a6e5f71043fa71863f8454775",
                    access_token="test_token_123"
                )
                self.assertEqual(account_id, "act_12345678")

    def test_get_fb_client_disabled_status(self):
        """Verify get_fb_client raises FacebookAccountDisabledError if the account is disabled in the DB."""
        with get_session() as db:
            social = SocialAccount(
                workspace_id=self.workspace_id,
                platform="facebook",
                account_name="Disabled Account",
                account_id="act_disabled_123",
                app_id="1726784475006075",
                app_secret="df47841a6e5f71043fa71863f8454775",
                access_token="token_abc",
                status="disabled"
            )
            db.add(social)
            db.commit()

            with self.assertRaises(FacebookAccountDisabledError):
                get_fb_client(str(self.workspace_id), db)

    @patch("core.integrations.fb_client.AdAccount")
    @patch("core.integrations.fb_client._execute_sdk_insights_call")
    def test_fetch_campaign_metrics_mapping(self, mock_execute_insights, mock_ad_account):
        """Verify fetch_campaign_metrics queries insights at the ad level and maps them using ad_mapper."""
        with get_session() as db:
            # Setup a platform variant and an ad mapper row for testing
            # We must satisfy database foreign key requirements
            from core.models import Workspace, MarketingCampaign, MasterContent
            
            ws = db.query(Workspace).filter_by(id=self.workspace_id).first()
            self.assertIsNotNone(ws, "Test Workspace must exist for tests.")
            
            campaign = db.query(MarketingCampaign).filter_by(workspace_id=ws.id).first()
            if not campaign:
                campaign = MarketingCampaign(
                    workspace_id=ws.id,
                    name="Test MAB Campaign for Insights",
                    status="active",
                    budget=10000.0
                )
                db.add(campaign)
                db.commit()
                db.refresh(campaign)
                
            master = db.query(MasterContent).filter_by(campaign_id=campaign.id).first()
            if not master:
                master = MasterContent(
                    workspace_id=ws.id,
                    campaign_id=campaign.id,
                    core_message="Mock Core Message",
                    approval_status="approved"
                )
                db.add(master)
                db.commit()
                db.refresh(master)
                
            pv = PlatformVariant(
                workspace_id=ws.id,
                master_content_id=master.id,
                platform="facebook",
                adapted_copy="Adapted Copy for MAB mapping",
                publish_status="published"
            )
            db.add(pv)
            db.commit()
            db.refresh(pv)
            
            # Seed ad mapper
            db.query(AdMapper).filter_by(platform_ad_id="fb_ad_100").delete()
            db.commit()
            
            mapper = AdMapper(
                variant_id=pv.id,
                platform_ad_id="fb_ad_100"
            )
            db.add(mapper)
            db.commit()

            # Mock insights API response
            mock_insight_response = [
                {
                    'ad_id': 'fb_ad_100',
                    'ad_name': 'Variant 1 Ad',
                    'impressions': '1500',
                    'clicks': '75',
                    'spend': '150.00',
                    'cpc': '2.00',
                    'ctr': '0.05',
                    'actions': [
                        {'action_type': 'offsite_conversion.fb_pixel_purchase', 'value': '5'}
                    ]
                }
            ]
            mock_execute_insights.return_value = mock_insight_response

            metrics = fetch_campaign_metrics("camp_fb_999", "act_12345678", db)
            
            self.assertEqual(len(metrics), 1)
            mapped = metrics[0]
            self.assertEqual(mapped["variant_id"], pv.id)
            self.assertEqual(mapped["platform_ad_id"], "fb_ad_100")
            self.assertEqual(mapped["impressions"], 1500)
            self.assertEqual(mapped["clicks"], 75)
            self.assertEqual(mapped["spend"], 150.0)
            self.assertEqual(mapped["cpc"], 2.0)
            self.assertEqual(mapped["ctr"], 0.05)
            self.assertEqual(mapped["conversions"], 5)
            self.assertEqual(mapped["cpa"], 30.0)

            # Cleanup
            db.query(AdMapper).filter_by(platform_ad_id="fb_ad_100").delete()
            db.query(PlatformVariant).filter_by(id=pv.id).delete()
            db.commit()

    @patch("core.integrations.fb_client.AdAccount")
    def test_fetch_campaign_metrics_disabled_api_error(self, mock_ad_account):
        """Verify fetch_campaign_metrics raises FacebookAccountDisabledError if Facebook API returns a restricted account error."""
        with get_session() as db:
            mock_instance = MagicMock()
            mock_ad_account.return_value = mock_instance
            
            # Create standard mock Facebook request error for disabled account
            # Error Code 100 with request_context={} to avoid TypeErrors
            mock_request_error = FacebookRequestError(
                message="Object with ID 'act_12345678' does not exist, cannot be loaded due to missing permissions, or is inactive/disabled.",
                request_context={},
                http_status=400,
                http_headers={},
                body={"error": {"message": "Account disabled", "code": 100}}
            )
            mock_instance.get_insights.side_effect = mock_request_error

            with self.assertRaises(FacebookAccountDisabledError):
                fetch_campaign_metrics("camp_123", "act_12345678", db)

    @patch("core.integrations.fb_client.get_fb_client")
    def test_init_facebook_client_success(self, mock_get_fb):
        """Verify init_facebook_client returns active API instance and account ID."""
        mock_api = MagicMock()
        mock_api.access_token = "valid_token"
        mock_get_fb.return_value = (mock_api, "12345678")
        
        with get_session() as db:
            api, acc_id, use_real = init_facebook_client(str(self.workspace_id), db)
            self.assertEqual(api, mock_api)
            self.assertEqual(acc_id, "act_12345678")
            self.assertTrue(use_real)

    @patch("core.integrations.fb_client.get_fb_client")
    def test_init_facebook_client_fallback(self, mock_get_fb):
        """Verify init_facebook_client falls back to mock if error occurs."""
        mock_get_fb.side_effect = Exception("Auth Failure")
        
        with get_session() as db:
            api, acc_id, use_real = init_facebook_client(str(self.workspace_id), db)
            self.assertIsNone(api)
            self.assertEqual(acc_id, "act_10509876_mock")
            self.assertFalse(use_real)

    @patch("facebook_business.adobjects.adcreative.AdCreative.remote_create")
    def test_batch_create_creatives_success(self, mock_remote_create):
        """Verify batch_create_creatives successfully builds and runs batch calls."""
        mock_api = MagicMock()
        mock_batch = MagicMock()
        mock_api.new_batch.return_value = mock_batch
        
        variants = [{"variant_id": str(uuid.uuid4()), "adapted_copy": "Variant Copy", "angle_name": "Logic"}]
        
        res = batch_create_creatives(mock_api, "act_123456", str(self.workspace_id), variants)
        
        mock_api.new_batch.assert_called_once()
        mock_batch.execute.assert_called_once()
        mock_remote_create.assert_called_once()

    @patch("facebook_business.adobjects.ad.Ad.remote_create")
    def test_batch_create_ads_success(self, mock_ad_remote_create):
        """Verify batch_create_ads successfully queries AdSet and executes ad batch creation."""
        mock_api = MagicMock()
        mock_batch = MagicMock()
        mock_api.new_batch.return_value = mock_batch
        
        variants = [{"variant_id": "00000000-0000-0000-0000-000000000004", "creative_id": "c123"}]
        
        with get_session() as db:
            res = batch_create_ads(mock_api, "act_123456", self.workspace_id, variants, db)
            mock_api.new_batch.assert_called_once()
            mock_batch.execute.assert_called_once()
            mock_ad_remote_create.assert_called_once()

    def test_save_publisher_state_success(self):
        """Verify save_publisher_state correctly persists master content, variants, and mappings atomically."""
        from core.models import Workspace, MarketingCampaign, MasterContent, PlatformVariant, AdMapper
        
        with get_session() as db:
            ws = db.query(Workspace).filter_by(id=self.workspace_id).first()
            campaign = db.query(MarketingCampaign).filter_by(workspace_id=ws.id).first()
            if not campaign:
                campaign = MarketingCampaign(
                    workspace_id=ws.id,
                    name="Test Publisher Campaign",
                    status="active",
                    budget=10000.0
                )
                db.add(campaign)
                db.commit()
                db.refresh(campaign)
            
            v_id1 = str(uuid.uuid4())
            v_id2 = str(uuid.uuid4())
            variants = [
                {"variant_id": v_id1, "adapted_copy": "Copy 1", "angle_name": "Logic"},
                {"variant_id": v_id2, "adapted_copy": "Copy 2", "angle_name": "Urgency"}
            ]
            ad_mappings = {v_id1: "fb_ad_xyz1", v_id2: "fb_ad_xyz2"}
            
            save_publisher_state(db, ws.id, campaign.id, variants, ad_mappings, "act_123456")
            
            # Verify records saved in DB
            pv1 = db.query(PlatformVariant).filter_by(id=uuid.UUID(v_id1)).first()
            pv2 = db.query(PlatformVariant).filter_by(id=uuid.UUID(v_id2)).first()
            self.assertIsNotNone(pv1)
            self.assertIsNotNone(pv2)
            self.assertEqual(pv1.adapted_copy, "Copy 1")
            
            map1 = db.query(AdMapper).filter_by(variant_id=pv1.id).first()
            map2 = db.query(AdMapper).filter_by(variant_id=pv2.id).first()
            self.assertIsNotNone(map1)
            self.assertIsNotNone(map2)
            self.assertEqual(map1.platform_ad_id, "fb_ad_xyz1")
            self.assertEqual(map2.platform_ad_id, "fb_ad_xyz2")
            
            # Clean up test records
            db.delete(map1)
            db.delete(map2)
            db.delete(pv1)
            db.delete(pv2)
            # Find and delete master content generated
            db.query(MasterContent).filter_by(id=pv1.master_content_id).delete()
            db.commit()

    def test_get_fb_client_junction_table_success(self):
        """Verify get_fb_client resolves campaign's linked social account via CampaignSocialAccount junction table."""
        with get_session() as db:
            from core.models import MarketingCampaign
            
            # Create campaign
            campaign = MarketingCampaign(
                workspace_id=self.workspace_id,
                name="Junction Linked Campaign",
                status="active",
                budget=5000.0
            )
            db.add(campaign)
            db.commit()
            db.refresh(campaign)

            # Create specific social account
            social = SocialAccount(
                workspace_id=self.workspace_id,
                platform="facebook",
                account_name="Junction Target Account",
                account_id="act_junction_777",
                app_id="1726784475006075",
                app_secret="df47841a6e5f71043fa71863f8454775",
                access_token="junction_token_777",
                status="active"
            )
            db.add(social)
            db.commit()
            db.refresh(social)

            # Link them via CampaignSocialAccount
            link = CampaignSocialAccount(
                campaign_id=campaign.id,
                social_account_id=social.id
            )
            db.add(link)
            db.commit()

            with patch("core.integrations.fb_client.FacebookAdsApi") as mock_api:
                mock_api_instance = MagicMock()
                mock_api.init.return_value = mock_api_instance
                mock_api.get_default_api.return_value = mock_api_instance
                
                api, account_id = get_fb_client(str(self.workspace_id), db, campaign_id=str(campaign.id))
                
                self.assertEqual(account_id, "act_junction_777")
                
            # Clean up
            db.delete(link)
            db.delete(social)
            db.delete(campaign)
            db.commit()

    def test_get_fb_client_legacy_fallback_success(self):
        """Verify get_fb_client successfully falls back to campaign.kpi_targets.social_account_id when no junction exists."""
        with get_session() as db:
            from core.models import MarketingCampaign
            
            # Create specific social account
            social = SocialAccount(
                workspace_id=self.workspace_id,
                platform="facebook",
                account_name="Legacy JSON Account",
                account_id="act_legacy_888",
                app_id="1726784475006075",
                app_secret="df47841a6e5f71043fa71863f8454775",
                access_token="legacy_token_888",
                status="active"
            )
            db.add(social)
            db.commit()
            db.refresh(social)

            # Create campaign with JSON target
            campaign = MarketingCampaign(
                workspace_id=self.workspace_id,
                name="Legacy JSON Campaign",
                status="active",
                budget=5000.0,
                kpi_targets={"social_account_id": str(social.id)}
            )
            db.add(campaign)
            db.commit()
            db.refresh(campaign)

            with patch("core.integrations.fb_client.FacebookAdsApi") as mock_api:
                mock_api_instance = MagicMock()
                mock_api.init.return_value = mock_api_instance
                mock_api.get_default_api.return_value = mock_api_instance
                
                api, account_id = get_fb_client(str(self.workspace_id), db, campaign_id=str(campaign.id))
                
                self.assertEqual(account_id, "act_legacy_888")
                
            # Clean up
            db.delete(social)
            db.delete(campaign)
            db.commit()

    def test_get_fb_client_workspace_fallback_success(self):
        """Verify get_fb_client falls back to default workspace active account when campaign is unmapped."""
        with get_session() as db:
            from core.models import MarketingCampaign
            
            # Create workspace default active account
            social = SocialAccount(
                workspace_id=self.workspace_id,
                platform="facebook",
                account_name="Workspace Default Account",
                account_id="act_default_ws_999",
                app_id="1726784475006075",
                app_secret="df47841a6e5f71043fa71863f8454775",
                access_token="default_ws_token_999",
                status="active"
            )
            db.add(social)
            db.commit()
            db.refresh(social)

            # Create unmapped campaign (empty kpi_targets, no junction table links)
            campaign = MarketingCampaign(
                workspace_id=self.workspace_id,
                name="Unmapped Campaign",
                status="active",
                budget=5000.0,
                kpi_targets={}
            )
            db.add(campaign)
            db.commit()
            db.refresh(campaign)

            with patch("core.integrations.fb_client.FacebookAdsApi") as mock_api:
                mock_api_instance = MagicMock()
                mock_api.init.return_value = mock_api_instance
                mock_api.get_default_api.return_value = mock_api_instance
                
                api, account_id = get_fb_client(str(self.workspace_id), db, campaign_id=str(campaign.id))
                
                self.assertEqual(account_id, "act_default_ws_999")
                
            # Clean up
            db.delete(social)
            db.delete(campaign)
            db.commit()

if __name__ == "__main__":
    unittest.main()
