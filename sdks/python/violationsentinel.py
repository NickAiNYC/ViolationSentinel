"""
ViolationSentinel Python SDK
Official Python client for the ViolationSentinel API

Installation:
    pip install violationsentinel

Usage:
    from violationsentinel import ViolationSentinelClient
    
    client = ViolationSentinelClient(
        api_key="your-api-key",
        tenant_id="your-tenant-id"
    )
    
    # List properties
    properties = client.properties.list()
    
    # Get property violations
    violations = client.violations.list(property_id="prop-123")
"""

import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


class ViolationSentinelError(Exception):
    """Base exception for ViolationSentinel SDK"""
    pass


class AuthenticationError(ViolationSentinelError):
    """Raised when authentication fails"""
    pass


class APIError(ViolationSentinelError):
    """Raised when API returns an error"""
    pass


class RateLimitError(ViolationSentinelError):
    """Raised when rate limit is exceeded"""
    pass


class ViolationSentinelClient:
    """Main client for ViolationSentinel API"""
    
    def __init__(
        self,
        api_key: str,
        tenant_id: str,
        base_url: str = "https://api.violationsentinel.com",
        timeout: int = 30
    ):
        """
        Initialize ViolationSentinel client
        
        Args:
            api_key: Your API key
            tenant_id: Your tenant ID
            base_url: Base URL for API (default: production)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.tenant_id = tenant_id
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        self.properties = PropertiesAPI(self)
        self.violations = ViolationsAPI(self)
        self.reports = ReportsAPI(self)
        self.webhooks = WebhooksAPI(self)
        self.analytics = AnalyticsAPI(self)
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}/api/v1{endpoint}"
        
        headers = {
            "X-API-Key": self.api_key,
            "X-Tenant-ID": self.tenant_id,
            "Content-Type": "application/json",
            "User-Agent": "ViolationSentinel-Python-SDK/1.0.0"
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
                timeout=self.timeout
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds"
                )
            
            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key or tenant ID")
            
            # Handle other errors
            if response.status_code >= 400:
                error_msg = response.json().get('detail', 'Unknown error')
                raise APIError(f"API error: {error_msg} (status: {response.status_code})")
            
            return response.json()
            
        except requests.RequestException as e:
            raise ViolationSentinelError(f"Request failed: {str(e)}")


class PropertiesAPI:
    """Properties API client"""
    
    def __init__(self, client: ViolationSentinelClient):
        self.client = client
    
    def list(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """List all properties"""
        return self.client._request(
            "GET",
            "/properties",
            params={"skip": skip, "limit": limit}
        )
    
    def get(self, property_id: str) -> Dict:
        """Get property by ID"""
        return self.client._request("GET", f"/properties/{property_id}")
    
    def create(
        self,
        name: str,
        bbl: str,
        address: Optional[str] = None,
        year_built: Optional[int] = None,
        units: Optional[int] = None
    ) -> Dict:
        """Create new property"""
        data = {
            "name": name,
            "bbl": bbl,
            "address": address,
            "year_built": year_built,
            "units": units
        }
        return self.client._request("POST", "/properties", json_data=data)
    
    def update(self, property_id: str, **kwargs) -> Dict:
        """Update property"""
        return self.client._request(
            "PUT",
            f"/properties/{property_id}",
            json_data=kwargs
        )
    
    def delete(self, property_id: str) -> None:
        """Delete property"""
        self.client._request("DELETE", f"/properties/{property_id}")


class ViolationsAPI:
    """Violations API client"""
    
    def __init__(self, client: ViolationSentinelClient):
        self.client = client
    
    def list(
        self,
        property_id: Optional[str] = None,
        source: Optional[str] = None,
        is_resolved: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict]:
        """List violations with filters"""
        params = {"skip": skip, "limit": limit}
        if property_id:
            params["property_id"] = property_id
        if source:
            params["source"] = source
        if is_resolved is not None:
            params["is_resolved"] = is_resolved
        
        return self.client._request("GET", "/violations", params=params)
    
    def get(self, violation_id: str) -> Dict:
        """Get violation by ID"""
        return self.client._request("GET", f"/violations/{violation_id}")
    
    def scan(
        self,
        property_ids: Optional[List[str]] = None,
        scan_all: bool = False,
        sources: List[str] = None
    ) -> Dict:
        """Trigger violation scan"""
        data = {
            "property_ids": property_ids,
            "scan_all": scan_all,
            "sources": sources or ["DOB", "HPD", "311"]
        }
        return self.client._request("POST", "/violations/scan", json_data=data)


class ReportsAPI:
    """Reports API client"""
    
    def __init__(self, client: ViolationSentinelClient):
        self.client = client
    
    def generate(
        self,
        property_ids: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_resolved: bool = False,
        format: str = "json"
    ) -> Dict:
        """Generate compliance report"""
        data = {
            "property_ids": property_ids,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "include_resolved": include_resolved,
            "format": format
        }
        return self.client._request("POST", "/reports", json_data=data)
    
    def get_status(self, report_id: str) -> Dict:
        """Get report generation status"""
        return self.client._request("GET", f"/reports/{report_id}")


class WebhooksAPI:
    """Webhooks API client"""
    
    def __init__(self, client: ViolationSentinelClient):
        self.client = client
    
    def list(self) -> List[Dict]:
        """List all webhooks"""
        return self.client._request("GET", "/webhooks")
    
    def create(
        self,
        url: str,
        events: List[str],
        is_active: bool = True
    ) -> Dict:
        """Create webhook subscription"""
        data = {
            "url": url,
            "events": events,
            "is_active": is_active
        }
        return self.client._request("POST", "/webhooks", json_data=data)
    
    def delete(self, webhook_id: str) -> None:
        """Delete webhook"""
        self.client._request("DELETE", f"/webhooks/{webhook_id}")


class AnalyticsAPI:
    """Analytics API client"""
    
    def __init__(self, client: ViolationSentinelClient):
        self.client = client
    
    def dashboard(self) -> Dict:
        """Get dashboard metrics"""
        return self.client._request("GET", "/analytics/dashboard")
    
    def violation_stats(self) -> Dict:
        """Get violation statistics"""
        return self.client._request("GET", "/analytics/violations/stats")


# Example usage
if __name__ == "__main__":
    # Initialize client
    client = ViolationSentinelClient(
        api_key="your-api-key",
        tenant_id="your-tenant-id"
    )
    
    # List properties
    properties = client.properties.list()
    print(f"Found {len(properties)} properties")
    
    # Create property
    new_property = client.properties.create(
        name="123 Main Street",
        bbl="1012650001",
        address="123 Main St, New York, NY 10001",
        year_built=1950,
        units=24
    )
    print(f"Created property: {new_property['id']}")
    
    # Get violations
    violations = client.violations.list(
        property_id=new_property['id'],
        is_resolved=False
    )
    print(f"Found {len(violations)} open violations")
    
    # Trigger scan
    scan_result = client.violations.scan(
        property_ids=[new_property['id']],
        sources=["DOB", "HPD", "311"]
    )
    print(f"Scan started: {scan_result['scan_id']}")
    
    # Get dashboard metrics
    metrics = client.analytics.dashboard()
    print(f"Total violations: {metrics['total_violations']}")
    
    # Generate report
    report = client.reports.generate(
        property_ids=[new_property['id']],
        format="pdf"
    )
    print(f"Report generating: {report['report_id']}")
