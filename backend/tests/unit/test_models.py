"""
Unit tests for data models
"""

import pytest
from uuid import uuid4
from backend.data_models.property import Property
from backend.data_models.user import Organization, SubscriptionTier


def test_property_creation():
    """Test property model creation"""
    org_id = uuid4()
    prop = Property(
        bbl="1012650001",
        address_line1="123 Main St",
        city="New York",
        state="NY",
        zip_code="10001",
        borough="MANHATTAN",
        organization_id=org_id
    )
    
    assert prop.bbl == "1012650001"
    assert prop.address_line1 == "123 Main St"
    assert prop.borough == "MANHATTAN"
    assert prop.organization_id == org_id


def test_organization_creation():
    """Test organization model creation"""
    org = Organization(
        name="Test Property Management",
        slug="test-pm",
        subscription_tier=SubscriptionTier.PRO
    )
    
    assert org.name == "Test Property Management"
    assert org.slug == "test-pm"
    assert org.subscription_tier == SubscriptionTier.PRO
    assert org.is_active is True
