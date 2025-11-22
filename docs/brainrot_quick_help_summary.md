# Quick Help Summary - Brain Rot Project

## TL;DR - What's Broken

**Step 1 can't collect trending topics data.**

### The Error
```
ERROR: 400 Unrecognized name: country_code at [9:17]
```

### The Code (failing)
```python
# scripts/brainrot/query_bigquery_trends.py:71
WHERE country_code = @country_code  # ← Column doesn't exist!
```

### What We Need
1. **Correct BigQuery schema** for `bigquery-public-data.google_trends.top_terms`
   - What columns exist?
   - How to filter by country (US/Italy)?
   - How to filter by date?

2. **OR working pytrends fallback**
   - Install: `pip install pytrends`
   - Verify it works for US and Italy

---

## Quick Test

**To reproduce the issue:**
```bash
cd /Users/nicholasbaro/Python/semant
python -c "
import asyncio
from scripts.brainrot.main_pipeline import BrainRotPipeline

async def test():
    pipeline = BrainRotPipeline()
    await pipeline._step_1_query_trends()

asyncio.run(test())
"
```

**Expected:** Should collect trending topics  
**Actual:** Returns empty lists, no data saved to GCS

---

## Files to Fix

1. **`scripts/brainrot/query_bigquery_trends.py`** (Line 71)
   - Fix the WHERE clause to use correct column names

2. **`scripts/brainrot/pytrends_fallback.py`** (Optional)
   - Verify pytrends implementation is correct

---

## Success Criteria

Step 1 works when:
- ✅ Returns actual trending topics (not empty list)
- ✅ Saves data to `gs://brainrot-trends/us_trends/raw/trends_*.json`
- ✅ Saves data to `gs://brainrot-trends/italian_trends/raw/trends_*.json`
- ✅ JSON files contain real data

---

## Full Details

See: `docs/brainrot_developer_help_request.md` for complete technical details.

