#!/bin/bash

echo "🚀 PrestaShop Inspector Setup & Execution"

# 1. Setup virtual environment
echo "📦 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Run tests locally
echo "🧪 Running tests..."
python -m pytest test_inspector.py -v

# 3. For remote execution
echo ""
echo "📋 MANUAL STEPS FOR REMOTE INSPECTION:"
echo ""
echo "1. Copy files to server:"
echo "   scp prestashop_inspector.py 51.255.70.134:/tmp/"
echo "   scp remote_inspection.sh 51.255.70.134:/tmp/"
echo ""
echo "2. Execute on server:"
echo "   ssh 51.255.70.134"
echo "   cd /tmp"
echo "   python3 prestashop_inspector.py"
echo ""
echo "3. Or use automated script:"
echo "   ./remote_inspection.sh"
echo ""
echo "📋 MANUAL CHECKLIST: See manual_checks.md"

deactivate