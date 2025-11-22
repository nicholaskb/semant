# Brain Rot Project - Developer Help Request

**Date:** 2025-11-19  
**Project:** Italian Brain Rot Content Generation Pipeline  
**Status:** Code complete, but Step 1 data collection failing

---

## Project Overview

We're building a pipeline to generate viral "Italian brain rot" content by:
1. Collecting trending topics from US and Italy
2. Tokenizing and filtering words
3. Using AI (Gemini) to pair Italian phrases with American objects
4. Generating images via Midjourney

**Tech Stack:**
- Python 3.11
- Google Cloud (BigQuery, GCS, Vertex AI)
- NLTK for tokenization
- Pytrends (fallback for Google Trends)
- Midjourney API

---

## Current Status

### ✅ What's Working

1. **Code Structure** - All 4 pipeline steps implemented
2. **Tests** - 35/35 tests passing
3. **Error Handling** - Graceful fallbacks throughout
4. **GCS Integration** - Bucket structure created, saving works
5. **AI Pairing Logic** - Fixed and tested (empty token check bug resolved)
6. **Configuration** - Centralized config system

### ❌ What's Broken

**CRITICAL ISSUE: Step 1 - Data Collection Failing**

---

## The Problem: Step 1 Data Collection

### What Should Happen

Step 1 queries Google BigQuery for trending topics and saves them to GCS:

```python
# Expected flow:
1. Query BigQuery: SELECT term, score, rank, week 
   FROM bigquery-public-data.google_trends.top_terms
   WHERE country_code = 'US' AND week >= start_date
2. Save results to: gs://brainrot-trends/us_trends/raw/trends_TIMESTAMP.json
3. Repeat for Italy (country_code = 'IT')
4. Fallback to pytrends if BigQuery fails
```

### What's Actually Happening

**Error 1: BigQuery Schema Mismatch**
```
ERROR: 400 Unrecognized name: country_code at [9:17]
Location: query, message: Unrecognized name: country_code at [9:17]
```

**Current Query (failing):**
```sql
SELECT 
    term,
    score,
    rank,
    week
FROM `bigquery-public-data.google_trends.top_terms`
WHERE 
    country_code = @country_code  -- ← This column doesn't exist!
    AND week >= @start_date
    AND week <= @end_date
ORDER BY score DESC
LIMIT @limit
```

**Error 2: Pytrends Fallback Not Available**
```
WARNING: pytrends not installed. Install with: pip install pytrends
```

**Result:**
- Step 1 completes without crashing
- But produces **ZERO data** (empty lists)
- GCS bucket remains empty
- All subsequent steps blocked

---

## Technical Details

### File: `scripts/brainrot/query_bigquery_trends.py`

**Current Implementation:**
```python
def query_trending_topics(self, country_code: str, weeks: int = 1, limit: int = 100):
    query = f"""
    SELECT term, score, rank, week
    FROM `{config.bigquery_dataset}.{config.bigquery_table}`
    WHERE 
        country_code = @country_code  -- ← Problem here
        AND week >= @start_date
        AND week <= @end_date
    ORDER BY score DESC
    LIMIT @limit
    """
```

**Config:**
```python
bigquery_dataset: str = "bigquery-public-data.google_trends"
bigquery_table: str = "top_terms"
```

### What We Need

1. **Correct BigQuery Schema**
   - Need to know actual column names in `bigquery-public-data.google_trends.top_terms`
   - How to filter by country (US vs Italy)?
   - How to filter by date range?
   - What columns are actually available?

2. **OR Working Pytrends Fallback**
   - Install pytrends: `pip install pytrends`
   - Verify it can fetch trending topics for US and Italy
   - Ensure rate limiting is handled

---

## Questions for Expert Developer

### 1. BigQuery Schema Investigation

**Question:** What is the actual schema of `bigquery-public-data.google_trends.top_terms`?

**What we need:**
- List of actual column names
- How to filter by country (US vs Italy)
- How to filter by date
- Sample query that works

**What we've tried:**
- Assumed `country_code` column exists (doesn't)
- Used parameterized queries (correct approach, wrong schema)

**Help needed:**
```sql
-- Can you provide a working query like:
SELECT * 
FROM `bigquery-public-data.google_trends.top_terms`
LIMIT 10;

-- And show us:
-- 1. What columns exist?
-- 2. How to filter by country?
-- 3. How to filter by date?
```

### 2. Alternative Data Sources

**Question:** If BigQuery dataset doesn't work, what alternatives exist?

**Options we're aware of:**
- Pytrends (unofficial Google Trends API)
- Google Trends API (if official one exists?)
- Other trending topics APIs?

**Help needed:**
- Recommendation on best approach
- Code example for working solution

### 3. Pytrends Implementation

**Question:** If we use pytrends, what's the correct implementation?

**Current code (may be wrong):**
```python
from pytrends.request import TrendReq

pytrends = TrendReq(hl='en-US', tz=360)
df = pytrends.trending_searches(pn='united_states')  # For US
df = pytrends.trending_searches(pn='italy')  # For Italy
```

**Help needed:**
- Verify this is correct
- Handle rate limiting
- Get daily/weekly trending topics
- Ensure it works for both US and Italy

---

## Code Context

### Relevant Files

1. **`scripts/brainrot/query_bigquery_trends.py`** (Lines 36-128)
   - BigQuery query implementation
   - Parameterized queries (correct approach)
   - Error handling and fallback logic

2. **`scripts/brainrot/pytrends_fallback.py`** (Lines 46-115)
   - Pytrends implementation
   - Country code mapping
   - DataFrame handling

3. **`scripts/brainrot/config.py`**
   - Configuration for dataset/table names
   - Time ranges, limits, etc.

4. **`scripts/brainrot/main_pipeline.py`** (Lines 93-145)
   - Step 1 orchestration
   - BigQuery → Pytrends fallback logic

### Error Logs

**Actual error when running Step 1:**
```
2025-11-19 16:12:06.430 | INFO | Querying BigQuery for US trends (last 1 weeks)...
2025-11-19 16:12:07.595 | ERROR | BigQuery query failed: 400 Unrecognized name: country_code at [9:17]
2025-11-19 16:12:07.595 | INFO | Falling back to pytrends for trending topics...
2025-11-19 16:12:08.017 | WARNING | ⚠️  No trending data available. Install pytrends: pip install pytrends
```

**GCS Verification:**
```bash
US trends files: 0
Italian trends files: 1 (just .gitkeep placeholder)
```

---

## What We've Verified

### ✅ Code Quality
- Parameterized queries (prevents SQL injection)
- Error handling (doesn't crash)
- Fallback logic (tries pytrends)
- GCS saving (works when data exists)

### ❌ Data Collection
- BigQuery query fails (schema issue)
- Pytrends not installed
- No data collected
- Empty GCS bucket

---

## Specific Help Requested

### Option 1: Fix BigQuery Query (Preferred)

**What we need:**
1. Correct schema for `bigquery-public-data.google_trends.top_terms`
2. Working query example for US and Italy trends
3. Date filtering approach
4. Updated code in `query_bigquery_trends.py`

**Example of what would help:**
```python
# If schema is different, show us:
query = """
SELECT 
    actual_column_name_1 as term,
    actual_column_name_2 as score,
    ...
FROM `bigquery-public-data.google_trends.top_terms`
WHERE 
    country_column = @country_code  -- ← correct column name
    AND date_column >= @start_date  -- ← correct date column
"""
```

### Option 2: Implement Pytrends Properly

**What we need:**
1. Verify pytrends installation: `pip install pytrends`
2. Correct usage for US and Italy
3. Rate limiting handling
4. Test that it actually returns data

**Example:**
```python
# Show us correct pytrends usage:
from pytrends.request import TrendReq

# For US trends
pytrends = TrendReq(hl='en-US', tz=360)
# ... correct method calls ...

# For Italy trends  
# ... correct method calls ...
```

### Option 3: Alternative Approach

**What we need:**
1. Different data source recommendation
2. Working code example
3. API keys/authentication requirements

---

## Environment Details

- **Python:** 3.11.8
- **Google Cloud Project:** `veo-gen-baro-1759717223`
- **GCS Bucket:** `brainrot-trends` (exists, accessible)
- **BigQuery:** Access available, but query failing
- **Location:** `us-central1`

**Dependencies:**
```python
# Installed:
google-cloud-bigquery>=3.13.0
google-cloud-storage

# Missing:
pytrends>=4.9.2  # Not installed
nltk>=3.8.1  # Not installed (but handled gracefully)
better-profanity>=0.7.0  # Not installed (but handled gracefully)
```

---

## Success Criteria

**Step 1 is working when:**
1. ✅ Query returns actual trending topics (not empty list)
2. ✅ Data saved to GCS: `gs://brainrot-trends/us_trends/raw/trends_*.json`
3. ✅ Data saved to GCS: `gs://brainrot-trends/italian_trends/raw/trends_*.json`
4. ✅ JSON files contain actual trending topic data
5. ✅ Can verify by checking GCS bucket contents

**Example of successful output:**
```json
[
  {
    "term": "iPhone 15",
    "score": 100,
    "rank": 1,
    "week": "2024-11-18",
    "country": "US"
  },
  ...
]
```

---

## Next Steps After Fix

Once Step 1 works:
1. ✅ Verify data in GCS
2. ✅ Run Step 2 (tokenization) with real data
3. ✅ Run Step 3 (AI pairing) with real data  
4. ✅ Run Step 4 (image generation) with real data
5. ✅ End-to-end pipeline test

---

## Contact & Context

**Codebase Location:** `/Users/nicholasbaro/Python/semant/scripts/brainrot/`

**Key Files:**
- `query_bigquery_trends.py` - BigQuery implementation (needs fix)
- `pytrends_fallback.py` - Pytrends implementation (needs verification)
- `main_pipeline.py` - Orchestration (calls Step 1)
- `config.py` - Configuration

**Test Files:**
- `tests/test_brainrot.py` - 35 tests (all passing, but test data is mocked)

---

## Summary

**The Issue:** Step 1 can't collect trending topics data because:
1. BigQuery query uses wrong schema (`country_code` doesn't exist)
2. Pytrends fallback not installed/configured

**What We Need:**
- Correct BigQuery schema/query
- OR working pytrends implementation
- OR alternative data source

**Impact:** Blocks entire pipeline (Steps 2-4 can't run without data)

**Priority:** CRITICAL - Nothing else can proceed until Step 1 works

---

**Thank you for your help!** 🙏

