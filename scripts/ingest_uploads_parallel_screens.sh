#!/bin/bash
#
# Parallel Image Ingestion Script using Screen Sessions
# 
# This script splits the ingestion job across multiple screen sessions,
# allowing you to process batches in parallel for faster completion.
#
# Usage:
#   ./scripts/ingest_uploads_parallel_screens.sh [num_screens] [max_concurrent]
#
# Examples:
#   ./scripts/ingest_uploads_parallel_screens.sh 4 8    # 4 screen sessions, 8 concurrent per session
#   ./scripts/ingest_uploads_parallel_screens.sh 8 5    # 8 screen sessions, 5 concurrent per session
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INGEST_SCRIPT="$PROJECT_ROOT/scripts/ingest_uploads_to_qdrant.py"
SCREEN_PREFIX="ingest_qdrant"

# Defaults
NUM_SCREENS=${1:-4}
MAX_CONCURRENT=${2:-8}

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Parallel Image Ingestion - Screen Sessions               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo -e "  Screen sessions: ${YELLOW}${NUM_SCREENS}${NC}"
echo -e "  Concurrent per session: ${YELLOW}${MAX_CONCURRENT}${NC}"
echo -e "  Script: ${INGEST_SCRIPT}"
echo ""

# Check if screen is installed
if ! command -v screen &> /dev/null; then
    echo -e "${YELLOW}⚠️  'screen' is not installed.${NC}"
    echo -e "${YELLOW}   Install with: brew install screen${NC}"
    exit 1
fi

# Check if Python script exists
if [ ! -f "$INGEST_SCRIPT" ]; then
    echo -e "${RED}❌ Script not found: $INGEST_SCRIPT${NC}"
    exit 1
fi

# Find all batches
cd "$PROJECT_ROOT"
BATCHES_DIR="uploads"
if [ ! -d "$BATCHES_DIR" ]; then
    echo -e "${RED}❌ Directory not found: $BATCHES_DIR${NC}"
    exit 1
fi

# Get list of batch directories (sorted)
BATCH_LIST=($(ls -d "$BATCHES_DIR"/batch_* 2>/dev/null | xargs -n1 basename | sort))
TOTAL_BATCHES=${#BATCH_LIST[@]}

if [ $TOTAL_BATCHES -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No batches found in $BATCHES_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}Found ${TOTAL_BATCHES} batches${NC}"
echo ""

# Calculate batches per screen
BATCHES_PER_SCREEN=$((TOTAL_BATCHES / NUM_SCREENS))
REMAINDER=$((TOTAL_BATCHES % NUM_SCREENS))

# Clean up any existing screens with same prefix
echo -e "${BLUE}Cleaning up existing screen sessions...${NC}"
screen -list 2>/dev/null | grep -E "\.${SCREEN_PREFIX}_[0-9]+" | cut -d. -f1 | awk '{print $1}' | xargs -r kill 2>/dev/null || true
sleep 1

# Create log directory
LOG_DIR="$PROJECT_ROOT/logs/ingestion_parallel"
mkdir -p "$LOG_DIR"

# Function to create a screen session for a range of batches
create_screen_session() {
    local session_num=$1
    local start_idx=$2
    local end_idx=$3
    local screen_name="${SCREEN_PREFIX}_${session_num}"
    local log_file="$LOG_DIR/screen_${session_num}.log"
    
    # Build batch name list for this session
    local session_batches=()
    for ((i=start_idx; i<end_idx; i++)); do
        if [ $i -lt ${#BATCH_LIST[@]} ]; then
            session_batches+=("${BATCH_LIST[$i]}")
        fi
    done
    
    if [ ${#session_batches[@]} -eq 0 ]; then
        return
    fi
    
    # Create screen session with command
    # Pass batch names as arguments
    local batch_args=""
    for batch in "${session_batches[@]}"; do
        batch_args="$batch_args --batch-names $batch"
    done
    
    local cmd="cd '$PROJECT_ROOT' && python3 '$INGEST_SCRIPT' --max-concurrent $MAX_CONCURRENT $batch_args 2>&1 | tee '$log_file'"
    
    screen -dmS "$screen_name" bash -c "$cmd"
    
    echo -e "${GREEN}✓ Created screen session: ${screen_name}${NC}"
    echo -e "   Batches: ${start_idx}-$((end_idx-1)) (${#session_batches[@]} batches)"
    echo -e "   Batch names: ${session_batches[*]}"
    echo -e "   Log: $log_file"
}

# Distribute batches across screens
current_idx=0
for ((screen_num=1; screen_num<=NUM_SCREENS; screen_num++)); do
    # Calculate how many batches this screen gets
    num_batches=$BATCHES_PER_SCREEN
    if [ $screen_num -le $REMAINDER ]; then
        num_batches=$((num_batches + 1))
    fi
    
    end_idx=$((current_idx + num_batches))
    
    if [ $current_idx -lt $TOTAL_BATCHES ]; then
        create_screen_session $screen_num $current_idx $end_idx
        current_idx=$end_idx
    fi
done

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Screen Sessions Created                                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}All screen sessions are running!${NC}"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  ${BLUE}screen -list${NC}                    # List all screen sessions"
echo -e "  ${BLUE}screen -r ${SCREEN_PREFIX}_1${NC}     # Attach to session 1"
echo -e "  ${BLUE}screen -r ${SCREEN_PREFIX}_2${NC}     # Attach to session 2"
echo -e "  ${BLUE}screen -x ${SCREEN_PREFIX}_1${NC}    # Attach without detaching others"
echo ""
echo -e "${YELLOW}Monitor progress:${NC}"
for ((i=1; i<=NUM_SCREENS; i++)); do
    echo -e "  ${BLUE}tail -f $LOG_DIR/screen_${i}.log${NC}"
done
echo ""
echo -e "${YELLOW}Stop all sessions:${NC}"
echo -e "  ${BLUE}screen -list | grep '${SCREEN_PREFIX}' | cut -d. -f1 | xargs kill${NC}"
echo ""
echo -e "${YELLOW}Check Qdrant progress:${NC}"
echo -e "  ${BLUE}python3 -c \"from qdrant_client import QdrantClient; c = QdrantClient(host='localhost', port=6333); print(f'Images: {c.get_collection(\\\"childrens_book_images\\\").points_count}')\"${NC}"
echo ""
echo -e "${GREEN}Logs directory: $LOG_DIR${NC}"
