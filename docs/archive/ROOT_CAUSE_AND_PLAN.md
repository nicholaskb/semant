# Root Cause Analysis & Fix Plan

## 🔍 Root Cause Identified

### The Problem
1. **Images exist in Qdrant** ✅ (with `gcs_url` in metadata)
2. **Images DO NOT exist in Knowledge Graph** ❌ (0 ImageObject nodes found)
3. **API fallback queries KG** → Finds nothing → Falls back to placeholder URI
4. **Result**: Images show "Image not available"

### Why This Happened
- Images were stored in Qdrant (via demo scripts or direct calls)
- But NOT stored in KG (KG was cleared, or ingestion failed, or different code path)
- The API's KG fallback finds nothing, so it uses placeholder `image_uri`

### Evidence
```
✅ Qdrant: Has images with gcs_url metadata
❌ KG: 0 ImageObject nodes found
❌ KG Query: Returns empty for test URI
```

## 📋 Fix Plan

### Option 1: Use Qdrant Metadata Directly (FASTEST) ⚡
**Problem**: API already checks Qdrant metadata first, but conversion might not be working

**Check**: Verify the API is actually extracting `gcs_url` from Qdrant metadata correctly

**Fix**: Ensure conversion logic runs on Qdrant metadata (should already work, but verify)

---

### Option 2: Backfill KG from Qdrant (COMPREHENSIVE) 🔄
**Problem**: Images in Qdrant but not in KG

**Solution**: Create a script to:
1. Query Qdrant for all images
2. Extract `gcs_url` from metadata
3. Create KG nodes with `schema:contentUrl` pointing to GCS URL
4. Store in KG

**Pros**: 
- Fixes existing images
- Makes KG fallback work
- Consistent data in both stores

**Cons**:
- Requires re-processing all images
- May need to generate embeddings again

---

### Option 3: Fix API to Use Qdrant Metadata Properly (IMMEDIATE) 🎯
**Problem**: API might not be extracting `gcs_url` correctly from Qdrant results

**Check**: 
1. Does Qdrant metadata have `gcs_url`? ✅ YES (diagnostic confirmed)
2. Is API extracting it? ❓ NEED TO VERIFY
3. Is conversion happening? ❓ NEED TO VERIFY

**Fix**: 
- Verify API code path for Qdrant metadata extraction
- Add logging to see what's actually happening
- Fix if conversion not working

---

## 🎯 Recommended Approach

### Step 1: Verify Current API Behavior
**Goal**: See exactly what the API is receiving and returning

**Method**: Add detailed logging to API endpoint:
- Log what Qdrant returns
- Log metadata extraction
- Log conversion result
- Log final `image_url` value

**Expected**: Should see `gcs_url` in metadata, conversion should work

---

### Step 2: Test Actual API Response
**Goal**: See what frontend actually receives

**Method**: 
1. Make API call: `curl -X POST http://localhost:8000/api/images/search-similar -F "image_file=@test.jpg"`
2. Inspect JSON response
3. Check if `image_url` field exists and has correct format

**Expected**: `image_url` should be `https://storage.googleapis.com/...`

---

### Step 3: Test GCS URL Accessibility
**Goal**: Verify GCS URLs are actually accessible

**Method**: 
```bash
# Take a URL from API response
curl -I "https://storage.googleapis.com/veo-videos-baro-1759717316/input_kids_monster/IMG_20230105_115024.jpg"
```

**Expected**: HTTP 200 OK
**If 403**: Bucket not public - need to make public or use signed URLs
**If 404**: Wrong path - need to fix path construction

---

### Step 4: Backfill KG (If Needed)
**Goal**: Ensure KG has image data for future fallback

**Method**: Create backfill script that:
1. Queries Qdrant for all images
2. Extracts `gcs_url` from metadata
3. Creates KG nodes with proper properties
4. Stores in KG

**When**: After confirming Qdrant metadata approach works

---

## 🔧 Implementation Priority

1. **FIRST**: Verify API is using Qdrant metadata correctly (should already work)
2. **SECOND**: Test actual API response to see what frontend gets
3. **THIRD**: Test GCS URL accessibility (likely 403 Forbidden issue)
4. **FOURTH**: Fix GCS public access OR implement signed URLs
5. **FIFTH**: Backfill KG for consistency

## ❓ Key Questions to Answer

1. ✅ Does Qdrant have `gcs_url`? **YES** (diagnostic confirmed)
2. ❓ Is API extracting `gcs_url` from Qdrant metadata? **NEED TO CHECK**
3. ❓ Is conversion happening? **NEED TO CHECK**
4. ❓ Are GCS URLs publicly accessible? **NEED TO TEST**
5. ❓ Is frontend receiving `image_url`? **NEED TO CHECK**

## 🚫 DO NOT CODE YET

Wait until we:
1. ✅ Verify API response contains `image_url` with correct format
2. ✅ Test if GCS URLs are accessible
3. ✅ Confirm root cause (likely GCS permissions OR API not extracting metadata)

Then implement the appropriate fix.

