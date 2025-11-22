#!/bin/bash
# Monitor the progress of the full pipeline run

echo "🔍 Monitoring Pipeline Progress"
echo "================================"
echo ""

# Check if process is running
if [ -f run_pid.txt ]; then
    PID=$(cat run_pid.txt)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Process is running (PID: $PID)"
    else
        echo "⚠️  Process completed or stopped"
    fi
else
    echo "⚠️  No PID file found"
fi

echo ""
echo "📊 Current Status:"
echo "------------------"

# Check Qdrant
echo -n "Qdrant embeddings: "
python3 -c "from qdrant_client import QdrantClient; c = QdrantClient(host='localhost', port=6333); print(c.get_collection('childrens_book_images').points_count)" 2>/dev/null || echo "Error checking"

# Check log file
if [ -f full_run_with_progress.log ]; then
    echo ""
    echo "📝 Recent Progress (last 10 lines):"
    echo "-----------------------------------"
    tail -10 full_run_with_progress.log | grep -E "Processing|batch|Paired|complete|✅|❌" || tail -5 full_run_with_progress.log
else
    echo "⚠️  Log file not found"
fi

echo ""
echo "💡 Run 'python verify_ingestion.py' for detailed verification"

