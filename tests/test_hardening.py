# tests/test_hardening.py
import os
import sys
import uuid
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from tenacity import RetryError

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.bandit_orchestrator import calculate_reward, solve_cold_start, compute_mab_beliefs
from core.ai_clients.llm_client import generate_text, _invoke_llm_with_retry
from graphs.autonomous_nodes import (
    scoring_node, action_selector_node, creative_generation_node,
    guardian_sandbox_node, insight_generator_node, publisher_node
)
from graphs.main_router import route_after_guardian

class TestSystemHardening(unittest.TestCase):
    
    # ──────────────────────────────────────────────────────────
    # Focus 1: Math & Reward Logic
    # ──────────────────────────────────────────────────────────
    def test_reward_zero_division(self):
        """Focus 1: Assert cpa=0, clicks=0, spend=0 calculates a valid reward 0.0 without zero-division."""
        metrics_zero = {
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
            "spend": 0.0
        }
        res_lead = calculate_reward(metrics_zero, "LEAD_GEN")
        res_brand = calculate_reward(metrics_zero, "BRAND_AWARENESS")
        
        self.assertEqual(res_lead, 0.0)
        self.assertEqual(res_brand, 0.0)
        
        # Test partially zero values
        metrics_partial = {
            "impressions": 1000,
            "clicks": 0,
            "conversions": 0,
            "spend": 100.0
        }
        res_lead_partial = calculate_reward(metrics_partial, "LEAD_GEN")
        self.assertEqual(res_lead_partial, 0.0)

    def test_epsilon_greedy_distribution(self):
        """Focus 1: Assert 80% Exploit and 20% Explore content mix distribution over 1,000 runs."""
        # Setup mock scoring actions
        state = {
            "selected_actions": [
                {"angle": "Social Proof", "belief": 0.8},
                {"angle": "Curiosity", "belief": 0.04},
                {"angle": "Urgency", "belief": 0.04},
                {"angle": "Fear", "belief": 0.04},
                {"angle": "Emotion", "belief": 0.04},
                {"angle": "Logic", "belief": 0.04}
            ]
        }
        
        exploit_count = 0
        explore_count = 0
        
        # Run action selector 1,000 times
        for _ in range(1000):
            res = action_selector_node(state)
            mix = [a["angle"] for a in res["selected_actions"]]
            
            # Request creates exactly 5 variants. Exploit gets 4 (80%), Explore gets 1 (20%)
            self.assertEqual(len(mix), 5)
            self.assertEqual(mix[:4].count("Social Proof"), 4)
            
            # Explore is the last item
            explore_angle = mix[4]
            if explore_angle == "Social Proof":
                exploit_count += 1
            else:
                explore_count += 1
                
        # With 5 options to choose for explore, the explore angle is selected randomly.
        # Ratio of exploit to explore mix components per variant generation is exactly 4/5 (80%) vs 1/5 (20%).
        print(f"\n[MAB MIX DISTRIBUTION] Exploit: {exploit_count}/1000, Explore: {explore_count}/1000")
        self.assertTrue(explore_count > 0)
        
    # ──────────────────────────────────────────────────────────
    # Focus 2: Stateless Graph Routing (Sandbox Retries)
    # ──────────────────────────────────────────────────────────
    def test_max_iteration_sandbox_fallback(self):
        """Focus 2: Assert brand compliance sandbox conditional edge routes back for retries but breaks after max 3 loop iterations."""
        # Scenario 1: First safety violation (rejection)
        state_first_fail = {
            "sandbox_feedbacks": [{"angle": "Fear", "score": 75, "reason": "unsafe"}]
        }
        dest_first = route_after_guardian(state_first_fail)
        self.assertEqual(dest_first, "creative_generation")
        
        # Scenario 2: Second safety violation (rejection)
        state_second_fail = {
            "sandbox_feedbacks": [
                {"angle": "Fear", "score": 75, "reason": "unsafe"},
                {"angle": "Fear", "score": 70, "reason": "unsafe"}
            ]
        }
        dest_second = route_after_guardian(state_second_fail)
        self.assertEqual(dest_second, "creative_generation")
        
        # Scenario 3: Third safety violation (exhaustion limit hit!)
        state_exhausted = {
            "sandbox_feedbacks": [
                {"angle": "Fear", "score": 75, "reason": "unsafe"},
                {"angle": "Fear", "score": 70, "reason": "unsafe"},
                {"angle": "Fear", "score": 65, "reason": "unsafe"}
            ]
        }
        dest_exhausted = route_after_guardian(state_exhausted)
        # Bypasses retry loop, routing straight to insight_generator to prevent freeze/zombie loop
        self.assertEqual(dest_exhausted, "insight_generator")

    # ──────────────────────────────────────────────────────────
    # Focus 3: Data Persistence (publisher_node Rollback)
    # ──────────────────────────────────────────────────────────
    @patch("graphs.autonomous.publisher.get_session")
    def test_database_rollback_atomicity(self, mock_session_ctx):
        """Focus 3: Verify that an Exception during publisher transaction triggers db.rollback() automatically with no orphans."""
        mock_db = MagicMock(spec=Session)
        mock_session_ctx.return_value.__enter__.return_value = mock_db
        
        # Mock commit to raise exception when mapper is inserted / committed
        mock_db.commit.side_effect = Exception("SQL Integrity Violation: Unique Constraint on AdMapper")
        
        state = {
            "workspace_id": "00000000-0000-0000-0000-000000000002",
            "campaign_id": "00000000-0000-0000-0000-000000000003",
            "generated_variants": [
                {"variant_id": "00000000-0000-0000-0000-000000000004", "adapted_copy": "test", "platform": "facebook"}
            ]
        }
        
        # Run node and expect Exception to bubble up
        with self.assertRaises(Exception):
            publisher_node(state)
            
        # Assert database rollback was triggered to prevent orphan records
        mock_db.rollback.assert_called_once()
        print(" -> Atomic publisher rollback validated successfully!")

    # ──────────────────────────────────────────────────────────
    # Edge Case 1: Absolute Cold-Start (Empty DB)
    # ──────────────────────────────────────────────────────────
    def test_absolute_cold_start_uniform_priors(self):
        """Edge Case 1: Assert empty DB results query returns NULL averages and automatically fallbacks to Uniform Priors."""
        mock_db = MagicMock(spec=Session)
        
        # Mock DB execute query to return empty row/None
        mock_db.execute.return_value.fetchone.return_value = None
        
        # Mock campaign metrics history as empty (no rows)
        mock_db.query.return_value.filter_by.return_value.all.return_value = []
        
        mab_res = compute_mab_beliefs(mock_db, str(uuid.uuid4()), "LEAD_GEN")
        
        # Should identify cold start and seed uniform priors (equal 1/6 probability weights)
        self.assertTrue(mab_res["cold_start"])
        beliefs = mab_res["beliefs"]
        self.assertEqual(len(beliefs), 6)
        for angle in beliefs:
            self.assertAlmostEqual(beliefs[angle], 1.0 / 6.0)

    # ──────────────────────────────────────────────────────────
    # Edge Case 2: LLM Format Mutation (Malformed JSON)
    # ──────────────────────────────────────────────────────────
    @patch("graphs.autonomous.insight.get_session")
    @patch("graphs.autonomous.insight.generate_text")
    def test_llm_format_mutation_json_repair(self, mock_gen_text, mock_session_ctx):
        """Edge Case 2: Assert insight_generator_node successfully cleans up and parses malformed wrapped JSON markdown output."""
        mock_db = MagicMock(spec=Session)
        mock_session_ctx.return_value.__enter__.return_value = mock_db
        
        # Mock LLM to return markdown wrapped json block
        mock_gen_text.return_value = "```json\n{\n  \"insight\": \"CPA reduction due to Social Proof focus\"\n}\n```"
        
        state = {
            "workspace_id": "00000000-0000-0000-0000-000000000002",
            "campaign_id": "00000000-0000-0000-0000-000000000003",
            "current_metrics": {},
            "current_beliefs": {}
        }
        
        res = insight_generator_node(state)
        self.assertEqual(res["sop_stage"], "publisher")
        
        # Verify Pending Insight insertion
        calls = mock_db.add.call_args_list
        self.assertTrue(len(calls) > 0)
        pending_record = calls[0][0][0]
        self.assertEqual(pending_record.insight_text, "CPA reduction due to Social Proof focus")
        print(" -> Malformed JSON cleaning and parsing validated successfully!")

    # ──────────────────────────────────────────────────────────
    # Edge Case 3: Rate Limits & API Timeout
    # ──────────────────────────────────────────────────────────
    def test_rate_limits_api_timeout_retry(self):
        """Edge Case 3: Assert tenacity retry decorator wraps LLM completions and retries on errors before failing."""
        mock_model = MagicMock()
        
        # Setup model.invoke to raise Rate Limit error (429) twice, then succeed on 3rd attempt
        call_count = 0
        def invoke_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Ollama HTTP 429 Too Many Requests")
            mock_resp = MagicMock()
            mock_resp.content = "Success on attempt 3"
            return mock_resp
            
        mock_model.invoke.side_effect = invoke_side_effect
        
        # Trigger retry wrapper
        res = _invoke_llm_with_retry(mock_model, [])
        
        # Tenacity should retry automatically and succeed
        self.assertEqual(res.content, "Success on attempt 3")
        self.assertEqual(call_count, 3)
        print(" -> Tenacity API rate limit backoff retries validated successfully!")

    def test_rate_limits_api_timeout_exhaustion(self):
        """Edge Case 3: Assert retry fails and raises Exception when errors persist beyond maximum attempts (3)."""
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("Ollama API TimeoutError Connection Refused")
        
        # tenacity raises Exception (reraised original exception) when all attempts are exhausted
        with self.assertRaises(Exception) as ctx:
            _invoke_llm_with_retry(mock_model, [])
        self.assertIn("Ollama API TimeoutError Connection Refused", str(ctx.exception))
            
        print(" -> Tenacity maximum attempts exhaustion validated successfully!")

if __name__ == "__main__":
    unittest.main()
