"""
NYC Open Data ingestion & normalization

Handles fetching and parsing data from NYC Open Data API (SOCRATA).
"""

from .dob_engine import DOBViolationMonitor, fetch_dob_violations

__all__ = ["DOBViolationMonitor", "fetch_dob_violations"]
