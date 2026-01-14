#!/usr/bin/env python3
"""
ViolationSentinel Setup Script
"""

import os
import sys
import subprocess

print("🚀 ViolationSentinel Setup")
print("=" * 50)

# Check Python
print("\n🐍 Checking Python...")
try:
    result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
    print(f"  ✅ {result.stdout.strip()}")
except:
    print("  ❌ Python3 not found")
    sys.exit(1)

# Check dependencies
print("\n📦 Checking dependencies...")
try:
    import pandas
    import fastapi
    print(f"  ✅ pandas {pandas.__version__}")
    print(f"  ✅ fastapi {fastapi.__version__}")
except ImportError:
    print("  ⚠️  Installing dependencies...")
    subprocess.run(['pip', 'install', '-r', 'requirements.txt'])

# Create necessary files
print("\n🔧 Setting up files...")
if not os.path.exists('users.json'):
    with open('users.json', 'w') as f:
        f.write('{}')
    print("  ✅ Created users.json")

if not os.path.exists('api_keys.json'):
    with open('api_keys.json', 'w') as f:
        f.write('{}')
    print("  ✅ Created api_keys.json")

print("\n✅ Setup complete!")
print("\n🎯 Next steps:")
print("1. Start API: ./start_api.sh")
print("2. Open: http://localhost:8000/docs")
print("3. Deploy: Upload landing_page.html to Netlify")
print("4. Sell: Send emails from docs/outreach_templates.md")
print("\n💰 First customer goal: TODAY")
print("=" * 50)
END && chmod +x setup.py