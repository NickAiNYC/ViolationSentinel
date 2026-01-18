"""
Test configuration and fixtures for ViolationSentinel.

Provides reusable fixtures for database sessions, test clients,
mock data, and API authentication.
"""

import os
import sys
from typing import Generator, Dict, Any
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Environment Configuration
# =============================================================================

# Set test environment variables before imports
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Get test database URL."""
    return os.environ.get("DATABASE_URL", "sqlite:///./test.db")


@pytest.fixture
def mock_db_session():
    """Create a mock database session for unit tests."""
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


# =============================================================================
# API Client Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Create a test client for the simple API."""
    try:
        from simple_api import app
        return TestClient(app)
    except ImportError:
        pytest.skip("simple_api not available")


@pytest.fixture
def backend_client():
    """Create a test client for the backend API."""
    try:
        from backend.app.main import app
        return TestClient(app)
    except ImportError:
        pytest.skip("backend.app.main not available")


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture
def test_api_key() -> str:
    """Return a test API key."""
    return "test-api-key-12345"


@pytest.fixture
def test_jwt_token() -> str:
    """Generate a test JWT token."""
    try:
        from backend.app.core.security import create_access_token
        token = create_access_token(
            data={"sub": "test@example.com", "tenant_id": "test-tenant"},
            expires_delta=timedelta(hours=1),
            scopes=["read", "write"]
        )
        return token
    except ImportError:
        return "test-jwt-token"


@pytest.fixture
def auth_headers(test_jwt_token: str) -> Dict[str, str]:
    """Return authentication headers for API requests."""
    return {
        "Authorization": f"Bearer {test_jwt_token}",
        "X-API-Key": "test-api-key",
        "Content-Type": "application/json"
    }


# =============================================================================
# Mock Data Fixtures
# =============================================================================

@pytest.fixture
def sample_bbl() -> str:
    """Return a sample BBL (Borough-Block-Lot) number."""
    return "3012650001"  # Brooklyn


@pytest.fixture
def sample_property() -> Dict[str, Any]:
    """Return a sample property data dictionary."""
    return {
        "id": "prop-123",
        "bbl": "3012650001",
        "address": "123 Main Street, Brooklyn, NY 11201",
        "borough": "BROOKLYN",
        "block": "01265",
        "lot": "0001",
        "year_built": 1965,
        "units": 24,
        "is_monitored": True,
        "risk_score": 65.5,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_violation() -> Dict[str, Any]:
    """Return a sample violation data dictionary."""
    return {
        "id": "viol-456",
        "property_id": "prop-123",
        "bbl": "3012650001",
        "source": "HPD",
        "violation_type": "Class C",
        "description": "Heat and hot water not provided",
        "issued_date": datetime(2024, 1, 15).isoformat(),
        "is_resolved": False,
        "fine_amount": 5000.00,
        "inspector_district": "brooklyn_council_36",
        "created_at": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_complaint_311() -> Dict[str, Any]:
    """Return a sample 311 complaint data dictionary."""
    return {
        "unique_key": "12345678",
        "created_date": datetime.now(timezone.utc).isoformat(),
        "closed_date": None,
        "complaint_type": "HEAT/HOT WATER",
        "descriptor": "ENTIRE BUILDING",
        "status": "Open",
        "bbl": "3012650001",
        "borough": "BROOKLYN",
        "incident_address": "123 Main Street"
    }


@pytest.fixture
def sample_hpd_violation() -> Dict[str, Any]:
    """Return a sample HPD violation data dictionary."""
    return {
        "violationid": "987654",
        "bbl": "3012650001",
        "buildingid": "12345",
        "apartment": "APT 2A",
        "inspectiondate": datetime(2024, 1, 15).isoformat(),
        "approveddate": datetime(2024, 1, 20).isoformat(),
        "novdescription": "Heat and hot water not provided",
        "violationstatus": "Open",
        "currentstatus": "VIOLATION OPEN",
        "class": "C",
        "ordernumber": "HPD123456"
    }


@pytest.fixture
def sample_dob_violation() -> Dict[str, Any]:
    """Return a sample DOB violation data dictionary."""
    return {
        "bin": "3012650",
        "bbl": "3012650001",
        "violation_number": "DOB-2024-001",
        "violation_type": "CONSTRUCTION",
        "issue_date": datetime(2024, 1, 10).isoformat(),
        "violation_category": "GENERAL",
        "description": "Work without permit",
        "device_number": None,
        "ecb_violation_number": "ECB-2024-001"
    }


@pytest.fixture
def sample_building_data() -> Dict[str, Any]:
    """Return sample building data for risk calculations."""
    return {
        "bbl": "3012650001",
        "year_built": 1965,
        "units": 24,
        "stories": 6,
        "building_class": "C2",
        "council_district": "brooklyn_council_36"
    }


@pytest.fixture
def portfolio_buildings() -> list:
    """Return a list of sample buildings for portfolio tests."""
    return [
        {"bbl": "3012650001", "year_built": 1950, "units": 12},  # Pre-1960
        {"bbl": "3012650002", "year_built": 1968, "units": 24},  # 1960-1973
        {"bbl": "1012650003", "year_built": 1985, "units": 48},  # Modern (Manhattan)
        {"bbl": "2012650004", "year_built": 1955, "units": 18},  # Pre-1960 (Bronx)
        {"bbl": "4012650005", "year_built": 2005, "units": 100}, # Modern (Queens)
    ]


# =============================================================================
# Mock External API Fixtures
# =============================================================================

@pytest.fixture
def mock_nyc_data_api():
    """Mock the NYC Open Data API responses."""
    mock = AsyncMock()
    mock.get_hpd_violations = AsyncMock(return_value=[])
    mock.get_dob_violations = AsyncMock(return_value=[])
    mock.get_311_complaints = AsyncMock(return_value=[])
    mock.get_permits = AsyncMock(return_value=[])
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client for caching tests."""
    mock = MagicMock()
    mock.get = MagicMock(return_value=None)
    mock.set = MagicMock(return_value=True)
    mock.setex = MagicMock(return_value=True)
    mock.delete = MagicMock(return_value=True)
    mock.ping = MagicMock(return_value=True)
    mock.zadd = MagicMock(return_value=1)
    mock.zcard = MagicMock(return_value=0)
    mock.zremrangebyscore = MagicMock(return_value=0)
    mock.expire = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_celery():
    """Mock Celery task queue."""
    mock = MagicMock()
    mock.delay = MagicMock(return_value=MagicMock(id="task-123"))
    mock.apply_async = MagicMock(return_value=MagicMock(id="task-123"))
    return mock


# =============================================================================
# Risk Engine Fixtures
# =============================================================================

@pytest.fixture
def heat_season_date() -> datetime:
    """Return a date during heat season (October-May)."""
    return datetime(2024, 2, 1)


@pytest.fixture
def off_season_date() -> datetime:
    """Return a date outside heat season (June-September)."""
    return datetime(2024, 7, 15)


@pytest.fixture
def high_risk_building() -> Dict[str, Any]:
    """Return data for a high-risk building."""
    return {
        "bbl": "3012650001",
        "year_built": 1950,  # Pre-1960 = 3.8x multiplier
        "council_district": "brooklyn_council_36",  # Hotspot = 2.3x
        "heat_complaints_30d": 5,  # High complaints
        "units": 24
    }


@pytest.fixture
def low_risk_building() -> Dict[str, Any]:
    """Return data for a low-risk building."""
    return {
        "bbl": "5012650001",  # Staten Island
        "year_built": 2010,  # Modern = 1.0x
        "council_district": None,  # No hotspot
        "heat_complaints_30d": 0,
        "units": 50
    }


# =============================================================================
# Async Test Support
# =============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Clean up any test files created during tests."""
    yield
    # Cleanup after test
    import glob
    for f in glob.glob("test*.db"):
        try:
            os.remove(f)
        except OSError:
            pass


# =============================================================================
# Markers
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )
