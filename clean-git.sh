#!/bin/bash

# Script to clean up git and recommit without venv
echo "🧹 Cleaning up git repository..."

cd "/Users/logeshtv/Documents/temp/disaster-prediction-/nlp 259/mainproject/backend"

# Check if we're in a git repo
if [ ! -d .git ]; then
    echo "❌ Not in a git repository"
    exit 1
fi

# Remove venv from git tracking (keep files locally)
echo "📝 Removing venv from git tracking..."
git rm -r --cached venv/ 2>/dev/null || true

# Also remove __pycache__ if tracked
git rm -r --cached __pycache__/ 2>/dev/null || true
git rm -r --cached utils/__pycache__/ 2>/dev/null || true

# Make sure .gitignore exists in backend
if [ ! -f .gitignore ]; then
    echo "📄 Creating backend .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Virtual Environment
venv/
ENV/
env/
.venv

# Environment variables
.env
.env.local

# IDEs
.vscode/
.idea/
*.swp
.DS_Store

# Logs
*.log
logs/

# Database
*.db
*.sqlite

# ML Models temp
*.pkl
*.joblib

# Testing
.pytest_cache/
.coverage
EOF
fi

# Add all files respecting .gitignore
echo "➕ Adding files..."
git add .

# Show status
echo ""
echo "📊 Git status:"
git status

echo ""
echo "✅ Ready to commit! Run:"
echo "   git commit -m 'chore: initialize backend without venv'"
echo "   git push"
