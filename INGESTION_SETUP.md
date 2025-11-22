# 🔧 Image Ingestion Setup Guide

**Date**: November 14, 2025  
**Status**: ⚠️ **BLOCKED - Need GCS Credentials**

---

## 🚨 Current Issue

**Problem**: Image ingestion is failing with 500 Internal Server Error

**Root Cause**: `GOOGLE_APPLICATION_CREDENTIALS` environment variable is NOT SET

**Impact**: Cannot upload images to GCS, which is required for the `/api/images/index` endpoint

---

## ✅ What's Working

- ✅ Qdrant: Running and accessible (localhost:6333)
- ✅ API Server: Running (localhost:8000)
- ✅ GCS_BUCKET_NAME: Set to `bahroo_public`
- ✅ Local Images: 3,324 images ready to ingest
- ✅ Ingestion Script: `scripts/ingest_local_images_to_qdrant.py` exists and works

---

## ❌ What's Broken

- ❌ **GOOGLE_APPLICATION_CREDENTIALS**: Not set
- ❌ **GCS Upload**: Failing (needs credentials)
- ❌ **Image Ingestion**: Cannot proceed without GCS upload

---

## 🔧 Fix Steps

### Step 1: Set Up GCS Credentials

1. **Get GCS Service Account Key**:
   - Go to Google Cloud Console
   - Create or use existing service account
   - Download JSON key file

2. **Set Environment Variable**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
   ```

3. **Add to .env file**:
   ```bash
   echo "GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json" >> .env
   ```

### Step 2: Restart API Server

The server needs to be restarted to pick up the new environment variable:

```bash
# Stop current server (Ctrl+C or kill process)
# Then restart:
python main.py
# OR
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3: Verify GCS Access

Test that GCS upload works:

```bash
python -c "
from google.cloud import storage
from config.settings import settings
import os

print(f'GCS_BUCKET_NAME: {settings.GCS_BUCKET_NAME}')
print(f'GOOGLE_APPLICATION_CREDENTIALS: {os.getenv(\"GOOGLE_APPLICATION_CREDENTIALS\", \"NOT SET\")}')

try:
    client = storage.Client()
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    print(f'✅ Can access bucket: {bucket.name}')
except Exception as e:
    print(f'❌ Cannot access bucket: {e}')
"
```

### Step 4: Run Ingestion

Once GCS credentials are set and server restarted:

```bash
python scripts/ingest_local_images_to_qdrant.py
```

**Expected**: Should upload 3,324 images successfully

---

## 📊 Alternative: Skip GCS Upload (Not Recommended)

If you want to test without GCS upload, you could modify the endpoint to skip GCS upload for local testing, but this is NOT recommended for production.

---

## 🎯 Next Steps

1. ⏳ **Set GOOGLE_APPLICATION_CREDENTIALS** (required)
2. ⏳ **Restart API server** (required)
3. ⏳ **Run ingestion script** (will work after steps 1-2)
4. ⏳ **Verify**: Check Qdrant has images

---

**Status**: ⚠️ **BLOCKED** - Waiting for GCS credentials setup.

