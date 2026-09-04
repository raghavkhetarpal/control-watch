import os
import pytest
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def test_engine():
    """Create an in-memory or test PostgreSQL connection."""
    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine(db_url)
    
    # In a real scenario, we would load schema.sql here
    # For now, we assume models will create their own tables or we use a dummy
    
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test DB session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def sample_holdings_df():
    """Sample pandas DataFrame mimicking parsed SEC N-PORT holdings data."""
    data = {
        "fund_id": [1, 1, 1],
        "report_date": ["2023-03-31", "2023-03-31", "2023-03-31"],
        "asset_cat": ["Equity", "Equity", "Fixed Income"],
        "pct_val": [40.0, 30.0, 30.0],
        "value": [40000.0, 30000.0, 30000.0]
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_fund_data():
    """Dict with fund info."""
    return {
        "fund_name": "Test Fund A",
        "cik": "0000000000",
        "series": "S000000000",
        "total_assets": 100000.0
    }

@pytest.fixture
def sample_exception_data():
    """Dict with exception data."""
    return {
        "exception_id": "EXC-001",
        "control_id": "DQ001",
        "status": "DETECTED",
        "severity": "HIGH",
        "description": "Missing required field: asset_cat"
    }
