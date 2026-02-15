#!/bin/bash
# CryptoPiggy Deployment Checklist Script
# Run this to verify everything is ready

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        CRYPTOPIGGY DEPLOYMENT READINESS CHECK                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

checks_passed=0
checks_total=0

# Check 1: Python installed
echo "Checking Python installation..."
checks_total=$((checks_total + 1))
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✅${NC} Python $python_version installed"
    checks_passed=$((checks_passed + 1))
else
    echo -e "${RED}❌${NC} Python not found"
fi
echo ""

# Check 2: Required files exist
echo "Checking required files..."
checks_total=$((checks_total + 1))
files_ok=true
for file in crypto_piggy_top.py app.py app_new.py requirements.txt; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file MISSING"
        files_ok=false
    fi
done
if [ "$files_ok" = true ]; then
    checks_passed=$((checks_passed + 1))
fi
echo ""

# Check 3: Test files exist
echo "Checking test files..."
checks_total=$((checks_total + 1))
test_files_ok=true
for file in test_app.py test_integration.py test_complete_flow.py validate_production_ready.py; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file MISSING"
        test_files_ok=false
    fi
done
if [ "$test_files_ok" = true ]; then
    checks_passed=$((checks_passed + 1))
fi
echo ""

# Check 4: Documentation complete
echo "Checking documentation..."
checks_total=$((checks_total + 1))
docs_ok=true
for file in OPERATIONAL_RUNBOOK.md PRODUCTION_READY_CHECKLIST.md BUGS_FIXED_FINAL.md FINAL_COMPLETION_REPORT.md; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file MISSING"
        docs_ok=false
    fi
done
if [ "$docs_ok" = true ]; then
    checks_passed=$((checks_passed + 1))
fi
echo ""

# Check 5: Python syntax validation
echo "Validating Python syntax..."
checks_total=$((checks_total + 1))
syntax_ok=true
for file in app_new.py app.py crypto_piggy_top.py test_complete_flow.py validate_production_ready.py; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $file - syntax OK"
    else
        echo -e "${RED}❌${NC} $file - syntax error"
        syntax_ok=false
    fi
done
if [ "$syntax_ok" = true ]; then
    checks_passed=$((checks_passed + 1))
fi
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    SUMMARY                                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo "Checks passed: $checks_passed/$checks_total"
echo ""

if [ $checks_passed -eq $checks_total ]; then
    echo -e "${GREEN}🎉 ALL CHECKS PASSED!${NC}"
    echo ""
    echo "Application is ready to deploy. Next steps:"
    echo ""
    echo "1. Install dependencies:"
    echo "   pip install -r requirements.txt"
    echo ""
    echo "2. Set environment variables:"
    echo "   export ALLOW_LIVE=1"
    echo "   export EXCHANGE=binanceus"
    echo "   export BACKEND_API_URL=http://localhost:8000"
    echo ""
    echo "3. Start the application:"
    echo "   streamlit run app_new.py"
    echo ""
    echo "4. Configure in the UI:"
    echo "   - Settings → API keys → Save → Validate & Sync"
    echo "   - Enable Live Trading"
    echo "   - Test with \$2 trade"
    echo ""
else
    checks_failed=$((checks_total - checks_passed))
    echo -e "${RED}❌ $checks_failed check(s) failed${NC}"
    echo ""
    echo "Please review the errors above before deploying."
fi
echo ""
