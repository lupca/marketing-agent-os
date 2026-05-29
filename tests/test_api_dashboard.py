# tests/test_api_dashboard.py
import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import fastapi_app
from db.connection import SessionLocal
from core.dashboard import auto_seed_dashboard_data

class TestDashboardAPI(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Prepare database and test client with startup events triggered."""
        cls.client_ctx = TestClient(fastapi_app)
        cls.client = cls.client_ctx.__enter__()
        
        # Ensure database is pre-seeded with dashboard mock metrics
        db = SessionLocal()
        try:
            auto_seed_dashboard_data(db)
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up test client context."""
        cls.client_ctx.__exit__(None, None, None)
            
    def test_dashboard_page_status(self):
        """Verify that GET /dashboard renders successfully."""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("CMO Strategic BI Dashboard", response.text)
        self.assertIn("cpaTrendChart", response.text)
        
    def test_api_dashboard_metrics(self):
        """Verify that GET /api/dashboard/metrics returns high-fidelity analytics."""
        response = self.client.get("/api/dashboard/metrics")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("anchor", data)
        self.assertIn("kpis", data)
        self.assertIn("winning_board", data)
        self.assertIn("killed_board", data)
        self.assertIn("trend_chart", data)
        self.assertIn("channel_data", data)
        self.assertIn("anti_patterns", data)
        
        # Verify specific calculations
        kpis = data["kpis"]
        self.assertGreater(kpis["ad_spend"], 0)
        self.assertGreater(kpis["total_conversions"], 0)
        self.assertGreater(kpis["blended_cac"], 0)
        self.assertEqual(kpis["ltv_cac_health"], "healthy")
        
    def test_api_dashboard_simulate(self):
        """Verify that POST /api/dashboard/simulate calculates sensitivity correctly."""
        payload = {
            "test_budget": 15000000.0,
            "price": 6000000.0,
            "cost": 2000000.0
        }
        response = self.client.post("/api/dashboard/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("inputs", data)
        self.assertIn("forecast", data)
        self.assertIn("allocations", data)
        
        inputs = data["inputs"]
        self.assertEqual(inputs["test_budget"], 15000000.0)
        self.assertEqual(inputs["margin"], 4000000.0)
        self.assertEqual(inputs["target_cpa"], 1200000.0) # 30% of margin
        
        forecast = data["forecast"]
        self.assertEqual(forecast["break_even_conversions"], 3.8) # 15M / 4M = 3.75 -> round to 3.8
        self.assertEqual(forecast["expected_conversions"], 12.5) # 15M / 1.2M = 12.5
        
        allocations = data["allocations"]
        self.assertTrue(len(allocations) > 0)
        for alloc in allocations:
            self.assertIn("channel", alloc)
            self.assertIn("allocated_budget", alloc)
            self.assertIn("weight_percent", alloc)

if __name__ == "__main__":
    unittest.main()
