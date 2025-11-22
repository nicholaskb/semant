# Diagnostic Plan: Why Images Aren't Showing

## Problem Statement
Images are still showing "Image not available" placeholders even after the fix. Need to identify root cause before implementing solution.

## Potential Root Causes

### 1. **GCS Bucket/Blob Not Public** ⚠️ MOST LIKELY
- **Issue**: Images stored in GCS but bucket/blob permissions don't allow public access
- **Symptom**: URLs are correct format (`https://storage.googleapis.com/bucket/path`) but return 403 Forbidden
- **Check**: Test if GCS URLs are actually accessible via HTTP

### 2. **Metadata Missing `gcs_url`**
- **Issue**: Qdrant metadata doesn't have `gcs_url` field
- **Symptom**: `image_url` falls back to placeholder `image_uri`
- **Check**: Inspect actual Qdrant payload data

### 3. **URL Conversion Not Happening**
- **Issue**: Conversion logic not executing or failing silently
- **Symptom**: `image_url` field missing or still contains `gs://` format
- **Check**: Inspect API response JSON

### 4. **Frontend Not Using `image_url`**
- **Issue**: Frontend code not updated or cached
- **Symptom**: Still using `image_uri` instead of `image_url`
- **Check**: Browser console/network tab

### 5. **CORS Issues**
- **Issue**: GCS bucket doesn't allow cross-origin requests
- **Symptom**: Images blocked by browser CORS policy
- **Check**: Browser console for CORS errors

## Diagnostic Steps (In Order)

### Step 1: Check What's Actually in Qdrant
**Goal**: Verify metadata structure and `gcs_url` presence

**Method**:
```python
# Query Qdrant directly to see payload
from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)

# Get a few sample points
points = client.scroll(
    collection_name="childrens_book_images",
    limit=5,
    with_payload=True
)

for point in points:
    print(f"Point ID: {point.id}")
    print(f"Payload: {point.payload}")
    print(f"Has gcs_url: {'gcs_url' in point.payload}")
    print("---")
```

**Expected**: Should see `gcs_url: "gs://bucket/path"` in payload
**If Missing**: Images were stored without `gcs_url` metadata

---

### Step 2: Check API Response
**Goal**: Verify API is returning `image_url` field with correct format

**Method**:
```bash
# Make actual API call and inspect response
curl -X POST http://localhost:8000/api/images/search-similar \
  -F "image_file=@test_image.jpg" \
  -F "limit=5" | jq '.results[0]'
```

**Check**:
- Does `image_url` field exist?
- Is it `https://storage.googleapis.com/...` format?
- Or is it still `http://example.org/image/...`?

**Expected**: `image_url: "https://storage.googleapis.com/bucket/path.jpg"`
**If Wrong**: Conversion logic not working or `gcs_url` missing

---

### Step 3: Test GCS URL Accessibility
**Goal**: Verify GCS URLs are actually publicly accessible

**Method**:
```bash
# Take a URL from API response and test it
curl -I "https://storage.googleapis.com/BUCKET_NAME/path/to/image.jpg"
```

**Check**:
- HTTP 200 = Public and accessible ✅
- HTTP 403 = Not public (permissions issue) ❌
- HTTP 404 = Wrong path/bucket ❌

**Expected**: HTTP 200 OK
**If 403**: Bucket/blob not public - **THIS IS LIKELY THE ISSUE**

---

### Step 4: Check Browser Console
**Goal**: See what errors browser is reporting

**Method**:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Upload image and search
4. Look for:
   - Network errors (404, 403, CORS)
   - JavaScript errors
   - Failed image loads

**Check**:
- Are images failing to load?
- What HTTP status codes?
- Any CORS errors?

---

### Step 5: Verify Frontend Code
**Goal**: Ensure frontend is using `image_url`

**Method**:
1. Check `static/frontend_image_search_example.html` line 403
2. Verify it uses: `result.image_url || result.image_uri`
3. Check browser cache (hard refresh: Cmd+Shift+R)

**Expected**: Code should use `image_url` first
**If Wrong**: Frontend not updated or cached

---

## Most Likely Root Cause

Based on code analysis:

**The images are stored in GCS with `gs://` URLs, but the GCS bucket/blobs are NOT PUBLIC.**

The `ImageIngestionAgent` downloads images FROM GCS (they already exist), but it doesn't make them public. It just stores the `gs://` reference. When we convert `gs://bucket/path` → `https://storage.googleapis.com/bucket/path`, the URL format is correct, but the bucket permissions prevent public access.

## Solution Plan (After Diagnosis Confirms)

### If GCS Not Public:
1. **Option A**: Make bucket public (if acceptable)
   - Set bucket IAM policy to allow public read
   - Or make individual blobs public

2. **Option B**: Use signed URLs (more secure)
   - Generate signed URLs with expiration
   - Requires GCS service account credentials
   - More secure but adds complexity

3. **Option C**: Proxy through API
   - Serve images through FastAPI endpoint
   - API authenticates with GCS
   - Returns image bytes with proper headers

### If Metadata Missing `gcs_url`:
1. Re-ingest images with proper metadata
2. Or query KG as fallback (already implemented)

### If Conversion Not Working:
1. Add logging to see what's happening
2. Fix conversion logic

## Next Steps

1. **Run diagnostics** to identify exact issue
2. **Confirm root cause** before implementing fix
3. **Implement appropriate solution** based on findings
4. **Test end-to-end** to verify images display

## Questions to Answer

1. ✅ Are images in Qdrant? (Check collection)
2. ✅ Do they have `gcs_url` in metadata? (Check payload)
3. ✅ Is API returning `image_url`? (Check response)
4. ❓ Are GCS URLs publicly accessible? (Test HTTP access)
5. ❓ Is frontend using `image_url`? (Check code + browser)

**Do NOT code until we confirm which issue it is!**

