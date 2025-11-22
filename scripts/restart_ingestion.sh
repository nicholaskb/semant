#!/bin/bash
# Quick restart script for image ingestion after reboot

set -e

echo "🔄 Restarting Image Ingestion After Reboot"
echo ""

# Step 1: Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "   Please start Docker Desktop first, then run this script again."
    exit 1
fi

# Step 2: Start Qdrant
echo "📦 Starting Qdrant..."
docker-compose up -d qdrant
sleep 5

# Step 3: Verify Qdrant
if curl -s http://localhost:6333/health > /dev/null; then
    echo "✅ Qdrant is running"
else
    echo "❌ Qdrant failed to start"
    exit 1
fi

# Step 4: Check current count
echo ""
echo "📊 Current Status:"
python3 -c "
from qdrant_client import QdrantClient
try:
    c = QdrantClient(host='localhost', port=6333)
    current = c.get_collection('childrens_book_images').points_count
    print(f'   Qdrant images: {current}')
    remaining = 4427 - (current - 4882) if current > 4882 else 4427
    print(f'   Remaining: ~{remaining} images')
    print(f'   Progress: {(current - 4882) / 4427 * 100:.1f}%' if current > 4882 else '   Progress: 0%')
except Exception as e:
    print(f'   Error: {e}')
"

# Step 5: Check if API server is running
echo ""
echo "🔍 Checking API server..."
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ API server is running"
else
    echo "⚠️  API server not running. Starting it..."
    cd "$(dirname "$0")/.."
    nohup python3 main.py > /tmp/api_server.log 2>&1 &
    echo "   Started in background (PID: $!)"
    echo "   Waiting 5 seconds for server to start..."
    sleep 5
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✅ API server is now running"
    else
        echo "❌ API server failed to start. Check /tmp/api_server.log"
        exit 1
    fi
fi

# Step 6: Restart ingestion
echo ""
echo "🚀 Restarting parallel ingestion..."
cd "$(dirname "$0")/.."
./scripts/ingest_uploads_parallel_screens.sh 4 8

echo ""
echo "✅ Ingestion restarted!"
echo ""
echo "📊 Monitor progress:"
echo "   ./scripts/monitor_parallel_ingestion.sh"
echo ""
echo "📝 View logs:"
echo "   tail -f logs/ingestion_parallel/screen_1.log"

