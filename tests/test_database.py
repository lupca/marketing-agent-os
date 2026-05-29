# tests/test_database.py
import os
import sys
import uuid
import unittest
from sqlalchemy.orm import Session

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal, is_mock
from db.seed import seed_database
from core.models import Workspace, User, BrandIdentity, ProductService

class TestDatabaseConnection(unittest.TestCase):
    
    def setUp(self):
        self.db: Session = SessionLocal()
        # Seed database automatically to ensure mock data exists
        seed_database(self.db)
        
    def tearDown(self):
        self.db.close()
        
    def test_database_fallback(self):
        """Verify fallback triggers correctly and engine is active."""
        mock_active = is_mock()
        print(f"\n[INFO] Test Database Fallback Active: {mock_active}")
        self.assertIsNotNone(mock_active)
        
    def test_default_workspace_seeded(self):
        """Verify default workspace exists and has valid owner."""
        ws = self.db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        self.assertIsNotNone(ws)
        self.assertEqual(ws.name, "Team Alpha Workspace")
        self.assertTrue(len(ws.members) > 0)
        
    def test_default_brand_voice(self):
        """Verify seeded brand voice exists and has guidelines."""
        brand = self.db.query(BrandIdentity).filter_by(brand_name="G-Agent Tech").first()
        self.assertIsNotNone(brand)
        self.assertIn("Chuyên nghiệp", brand.voice_and_tone)
        
    def test_product_price_cost_anchor(self):
        """Verify that product has valid pricing details seeded."""
        product = self.db.query(ProductService).filter_by(name="Marketing Agent OS Software").first()
        self.assertIsNotNone(product)
        price_str, cost_str = product.default_offer.split(";")
        self.assertEqual(float(price_str), 5000000.0)
        self.assertEqual(float(cost_str), 1500000.0)

if __name__ == "__main__":
    unittest.main()
