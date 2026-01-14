#!/bin/bash

# Simple Git Push Script for ViolationSentinel

echo "🚀 Preparing to push ViolationSentinel to GitHub..."
echo ""

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
    echo "✅ Git initialized"
fi

# Add all files
echo "📁 Adding files to git..."
git add .

# Commit
echo "💾 Creating commit..."
git commit -m "ViolationSentinel: NYC property risk intelligence platform" || echo "No changes to commit"

echo ""
echo "✅ Local git repository ready!"
echo ""
echo "📝 To push to GitHub:"
echo ""
echo "1. Create a new repository at https://github.com/new"
echo "   - Name: ViolationSentinel"
echo "   - Description: NYC Property Risk Intelligence Platform"
echo "   - Choose Public or Private"
echo "   - DO NOT initialize with README"
echo ""
echo "2. Run these commands:"
echo ""
echo "   git remote add origin https://github.com/YOUR_USERNAME/ViolationSentinel.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. (Optional) Enable GitHub Pages:"
echo "   - Go to Settings > Pages"
echo "   - Source: Deploy from a branch"
echo "   - Branch: main, folder: / (root)"
echo ""
echo "🎯 Next Steps After Pushing:"
echo "1. Deploy landing_page.html to Netlify (drag & drop)"
echo "2. Start API: ./start_api.sh"
echo "3. Send first 5 emails"
echo "4. Get first customer!"
echo ""
echo "💰 Remember: First customer = $297 MRR"
echo ""
END && chmod +x git_push.sh && echo '=== Final File List ===' && ls -la