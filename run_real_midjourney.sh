#!/bin/bash
# Script to run the real Midjourney integration with proper environment

export MIDJOURNEY_API_TOKEN="486a37ae667a6529e97262dad84535d821da8d290c405464b87033185c21836d"
export GCS_BUCKET_NAME="bahroo_public"
export GOOGLE_APPLICATION_CREDENTIALS="credentials/service_account.json"

echo "Environment variables set:"
echo "  MIDJOURNEY_API_TOKEN: ${MIDJOURNEY_API_TOKEN:0:10}..."
echo "  GCS_BUCKET_NAME: $GCS_BUCKET_NAME"
echo "  GOOGLE_APPLICATION_CREDENTIALS: $GOOGLE_APPLICATION_CREDENTIALS"
echo ""

python3 real_illustrated_book_workflow.py
