"""
Admin Tools for ViolationSentinel Monetization
Quick commands to manage users and payments
"""

import json
from simple_monetization import monetization
from datetime import datetime

class AdminTools:
    @staticmethod
    def list_users():
        """List all users"""
        print("\n📋 USERS LIST")
        print("=" * 60)
        for email, user in monetization.users.items():
            print(f"Email: {email}")
            print(f"  Tier: {user['tier']}")
            print(f"  API Key: {user['api_key']}")
            print(f"  Requests Used: {user['requests_used']}")
            print(f"  Created: {user['created']}")
            print("-" * 60)
    
    @staticmethod
    def add_user(email, tier="pro", payment_proof="manual"):
        """Add a new user"""
        api_key = monetization.create_user(email, tier, payment_proof)
        print(f"✅ User added: {email}")
        print(f"🔑 API Key: {api_key}")
        print(f"💳 Tier: {tier}")
        return api_key
    
    @staticmethod
    def reset_usage(email):
        """Reset user's usage counter"""
        if email in monetization.users:
            monetization.users[email]["requests_used"] = 0
            monetization.save_users()
            print(f"✅ Usage reset for {email}")
        else:
            print(f"❌ User not found: {email}")
    
    @staticmethod
    def upgrade_user(email, new_tier):
        """Upgrade user to new tier"""
        if email in monetization.users:
            monetization.users[email]["tier"] = new_tier
            monetization.save_users()
            print(f"✅ {email} upgraded to {new_tier} tier")
        else:
            print(f"❌ User not found: {email}")
    
    @staticmethod
    def stats():
        """Show business statistics"""
        print("\n📊 BUSINESS STATS")
        print("=" * 60)
        
        total_users = len(monetization.users)
        pro_users = sum(1 for u in monetization.users.values() if u["tier"] == "pro")
        enterprise_users = sum(1 for u in monetization.users.values() if u["tier"] == "enterprise")
        
        # Calculate MRR
        mrr = (pro_users * 297) + (enterprise_users * 999)
        
        print(f"Total Users: {total_users}")
        print(f"Pro Users: {pro_users}")
        print(f"Enterprise Users: {enterprise_users}")
        print(f"Monthly Recurring Revenue: ${mrr}")
        print(f"Estimated Monthly Profit: ${mrr * 0.85:.0f}")
        print("=" * 60)

if __name__ == "__main__":
    import sys
    
    admin = AdminTools()
    
    if len(sys.argv) < 2:
        print("Usage: python admin_tools.py [command] [args]")
        print("Commands:")
        print("  list                    - List all users")
        print("  add <email> [tier]      - Add new user")
        print("  reset <email>           - Reset user usage")
        print("  upgrade <email> <tier>  - Upgrade user tier")
        print("  stats                   - Show business stats")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        admin.list_users()
    elif command == "add" and len(sys.argv) >= 3:
        email = sys.argv[2]
        tier = sys.argv[3] if len(sys.argv) >= 4 else "pro"
        admin.add_user(email, tier)
    elif command == "reset" and len(sys.argv) >= 3:
        email = sys.argv[2]
        admin.reset_usage(email)
    elif command == "upgrade" and len(sys.argv) >= 4:
        email = sys.argv[2]
        tier = sys.argv[3]
        admin.upgrade_user(email, tier)
    elif command == "stats":
        admin.stats()
    else:
        print("Invalid command")
