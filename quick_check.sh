#!/bin/bash
# Quick pre-flight checks for Qdrant Image Search Demo

echo "🔍 Running pre-flight checks for Qdrant Image Search Demo..."
echo ""

ERRORS=0

# Check Qdrant
echo -n "Checking Qdrant... "
if curl -s http://localhost:6333/health > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ NOT running"
    echo "   Fix: docker run -d -p 6333:6333 qdrant/qdrant"
    ERRORS=$((ERRORS + 1))
fi

# Check OpenAI key
echo -n "Checking OPENAI_API_KEY... "
if [ -z "$OPENAI_API_KEY" ]; then
    # Check .env file
    if [ -f .env ] && grep -q "OPENAI_API_KEY" .env; then
        echo "✅ Found in .env file"
    else
        echo "❌ NOT set"
        echo "   Fix: export OPENAI_API_KEY=your_key or add to .env"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "✅ Set in environment"
fi

# Check Python dependencies
echo -n "Checking Python dependencies... "
if python3 -c "import openai, qdrant_client, PIL, numpy" 2>/dev/null; then
    echo "✅ Installed"
else
    echo "❌ Missing"
    echo "   Fix: pip install openai qdrant-client Pillow numpy"
    ERRORS=$((ERRORS + 1))
fi

# Check disk space (at least 100MB free)
echo -n "Checking disk space... "
if command -v df >/dev/null 2>&1; then
    AVAILABLE_GB=$(df -g . | tail -1 | awk '{print $4}')
    if [ -n "$AVAILABLE_GB" ] && [ "$AVAILABLE_GB" -gt 0 ]; then
        echo "✅ ${AVAILABLE_GB}GB available"
    else
        echo "⚠️  Could not check disk space"
    fi
else
    echo "⚠️  Could not check disk space"
fi

# Check port 8000 (for API server)
echo -n "Checking port 8000... "
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is in use"
    echo "   (This is OK if API server is already running)"
else
    echo "✅ Available"
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ All critical checks passed! Ready to run demo."
    echo ""
    echo "Next steps:"
    echo "  1. python demo_end_to_end_image_search.py"
    echo "  2. python main.py  (to start API server)"
    echo "  3. Open http://localhost:8000/static/frontend_image_search_example.html"
    exit 0
else
    echo "❌ Found $ERRORS critical issue(s). Please fix before running demo."
    exit 1
fi

