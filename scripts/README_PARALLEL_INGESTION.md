# Parallel Image Ingestion Guide

## What Happens When You Close Your Computer?

### ✅ **Closing Terminal/SSH Connection**
- **Screen sessions CONTINUE running** in the background
- You can reconnect anytime: `screen -r ingest_qdrant_1`
- Processes keep running even if you disconnect

### ⚠️ **Computer Sleeps**
- Processes may **pause** (macOS behavior)
- Network connections may **timeout**
- API calls may **fail** and need retry
- **Solution**: Use `caffeinate` to prevent sleep (see below)

### ❌ **Computer Shuts Down**
- All processes **STOP**
- Screen sessions are **TERMINATED**
- **Progress is LOST** (but Qdrant data persists - already ingested images stay)
- **Solution**: Keep computer awake or run on a server

## Preventing Sleep (macOS)

### Option 1: Use the No-Sleep Script
```bash
./scripts/ingest_with_no_sleep.sh 4 8
```
This automatically prevents sleep during ingestion.

### Option 2: Manual caffeinate
```bash
# Prevent sleep and run ingestion
caffeinate -d -i -m ./scripts/ingest_uploads_parallel_screens.sh 4 8
```

### Option 3: System Settings
- System Preferences → Energy Saver
- Set "Prevent computer from sleeping" during ingestion

## Checking Status After Reopening Computer

```bash
# Check if sessions are still running
screen -list

# Check Qdrant progress
python3 -c "from qdrant_client import QdrantClient; c = QdrantClient(host='localhost', port=6333); print(f'Images: {c.get_collection(\"childrens_book_images\").points_count}')"

# View logs
tail -f logs/ingestion_parallel/screen_1.log
```

## If Sessions Stopped

If your computer slept/shut down and sessions stopped:

1. **Check what was ingested:**
   ```bash
   python3 -c "from qdrant_client import QdrantClient; c = QdrantClient(host='localhost', port=6333); print(f'Current images: {c.get_collection(\"childrens_book_images\").points_count}')"
   ```

2. **Restart the ingestion:**
   ```bash
   ./scripts/ingest_uploads_parallel_screens.sh 4 8
   ```
   
   The script will skip already-ingested images (they're already in Qdrant), so it's safe to restart.

## Best Practices

1. **Keep computer awake** during ingestion (use `caffeinate`)
2. **Monitor progress** periodically: `./scripts/monitor_parallel_ingestion.sh`
3. **Don't shut down** until ingestion completes
4. **Safe to restart** - already-ingested images won't be duplicated

## Current Sessions

To see what's running:
```bash
screen -list
```

To attach to a session:
```bash
screen -r ingest_qdrant_1
```

To stop all sessions:
```bash
screen -list | grep 'ingest_qdrant' | cut -d. -f1 | xargs kill
```

