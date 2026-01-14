"""
Simple Cashflow System - Start earning TODAY without Stripe
"""

import json
import hashlib
from datetime import datetime
import pandas as pd

class SimpleMonetization:
    """Manual payment system for immediate cashflow"""
    
    def __init__(self):
        self.users_file = "users.json"
        self.api_keys_file = "api_keys.json"
        self.load_users()
    
    def load_users(self):
        try:
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        except:
            self.users = {}
        
        try:
            with open(self.api_keys_file, 'r') as f:
                self.api_keys = json.load(f)
        except:
            self.api_keys = {}
    
    def save_users(self):
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
        with open(self.api_keys_file, 'w') as f:
            json.dump(self.api_keys, f, indent=2)
    
    def create_user(self, email, tier="pro", payment_proof=None):
        """Create user after manual payment"""
        api_key = f"vs_{hashlib.sha256(f'{email}{datetime.now()}'.encode()).hexdigest()[:32]}"
        
        self.users[email] = {
            "email": email,
            "tier": tier,
            "api_key": api_key,
            "created": datetime.now().isoformat(),
            "payment_proof": payment_proof,
            "requests_used": 0,
            "month_start": datetime.now().replace(day=1).isoformat()
        }
        
        self.api_keys[api_key] = email
        self.save_users()
        
        return api_key
    
    def check_access(self, api_key):
        """Check if API key is valid"""
        if api_key not in self.api_keys:
            return False
        
        email = self.api_keys[api_key]
        user = self.users.get(email)
        
        if not user:
            return False
        
        # Check monthly limits
        tier_limits = {
            "free": 10,
            "pro": 1000,
            "enterprise": 10000
        }
        
        # Reset if new month
        month_start = datetime.fromisoformat(user["month_start"])
        current_month = datetime.now().replace(day=1)
        if month_start < current_month:
            user["requests_used"] = 0
            user["month_start"] = current_month.isoformat()
            self.save_users()
        
        limit = tier_limits.get(user["tier"], 0)
        return user["requests_used"] < limit
    
    def track_request(self, api_key):
        """Track API usage"""
        if api_key in self.api_keys:
            email = self.api_keys[api_key]
            if email in self.users:
                self.users[email]["requests_used"] += 1
                self.save_users()

# Instantiate globally
monetization = SimpleMonetization()
