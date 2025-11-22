#!/bin/bash
#
# Monitor Parallel Ingestion Progress
# 
# Shows progress from all screen sessions and Qdrant status
#
# Usage:
#   ./scripts/monitor_parallel_ingestion.sh
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs/ingestion_parallel"
SCREEN_PREFIX="ingest_qdrant"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Parallel Ingestion Monitor                              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check Qdrant status
echo -e "${GREEN}📊 Qdrant Status:${NC}"
python3 -c "
from qdrant_client import QdrantClient
try:
    c = QdrantClient(host='localhost', port=6333)
    info = c.get_collection('childrens_book_images')
    print(f'   Total images: {info.points_count}')
    print(f'   Status: {info.status}')
except Exception as e:
    print(f'   Error: {e}')
" 2>/dev/null || echo "   ⚠️  Could not connect to Qdrant"

echo ""

# List screen sessions
echo -e "${GREEN}🖥️  Screen Sessions:${NC}"
screen -list 2>/dev/null | grep -E "\.${SCREEN_PREFIX}_[0-9]+" || echo "   No active sessions found"

echo ""

# Show recent log activity
if [ -d "$LOG_DIR" ]; then
    echo -e "${GREEN}📝 Recent Activity (last 5 lines per session):${NC}"
    for log_file in "$LOG_DIR"/screen_*.log; do
        if [ -f "$log_file" ]; then
            session_name=$(basename "$log_file" .log | sed 's/screen_/Session /')
            echo -e "${BLUE}   $session_name:${NC}"
            tail -5 "$log_file" 2>/dev/null | sed 's/^/      /' | tail -3
            echo ""
        fi
    done
fi

echo -e "${YELLOW}Commands:${NC}"
echo -e "  ${BLUE}screen -list${NC}                    # List all sessions"
echo -e "  ${BLUE}screen -r ${SCREEN_PREFIX}_1${NC}     # Attach to session 1"
echo -e "  ${BLUE}watch -n 5 $0${NC}                   # Auto-refresh every 5s"

