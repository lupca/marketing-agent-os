# tests/test_database.py
import os
import sys
import pytest
from sqlalchemy.orm import Session

# Add root folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.seed import seed_database
from core.models import Workspace, User, BrandIdentity, ProductService

@pytest.fixture(autouse=True)
def setup_seed(db_session: Session):
    """Automatically seed the database before each test. Data is rolled back via db_session."""
    seed_database(db_session)


def test_default_workspace_seeded(db_session: Session):
    """Verify default workspace exists and has valid owner."""
    ws = db_session.query(Workspace).filter_by(name="Team Alpha Workspace").first()
    assert ws is not None
    assert ws.name == "Team Alpha Workspace"
    assert len(ws.members) > 0

def test_default_brand_voice(db_session: Session):
    """Verify seeded brand voice exists and has guidelines."""
    brand = db_session.query(BrandIdentity).filter_by(brand_name="G-Agent Tech").first()
    assert brand is not None
    assert "Chuyên nghiệp" in brand.voice_and_tone

def test_product_price_cost_anchor(db_session: Session):
    """Verify that product has valid pricing details seeded."""
    product = db_session.query(ProductService).filter_by(name="Marketing Agent OS Software").first()
    assert product is not None
    price_str, cost_str = product.default_offer.split(";")
    assert float(price_str) == 5000000.0
    assert float(cost_str) == 1500000.0
