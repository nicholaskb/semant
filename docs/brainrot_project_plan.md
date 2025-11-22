# Brain Rot Project Plan

## Overview
Generate viral "Italian brain rot" content by combining trending Italian phrases with trending American objects, creating humorous, viral-worthy image prompts.

## GCS Bucket Structure
- **Bucket Name**: `brainrot-trends`
- **Directory Structure**:
  ```
  brainrot-trends/
  ├── us_trends/            # US trending topics (renamed from american_trends)
  │   ├── raw/              # Raw BigQuery results
  │   ├── tokenized/        # Tokenized trending words
  │   └── selected/         # AI-selected combinations
  ├── italian_trends/
  │   ├── raw/              # Raw BigQuery results (Italy)
  │   ├── tokenized/        # Tokenized Italian words
  │   └── phrases/          # Generated Italian phrases
  ├── combinations/
  │   ├── ai_selections/    # AI-paired combinations
  │   └── final/            # Finalized prompts
  └── generated_images/     # Output images
  ```

## Pipeline 1: American Trending Topics

### Steps:
1. **Query Google BigQuery** for US trending topics
   - **Question**: Which dataset/table? (e.g., `bigquery-public-data.google_trends.top_terms`)
   - **Time Range**: Daily? Hourly? Weekly?
   - **Output**: List of trending topics/keywords

2. **Tokenize and Search Google Trends**
   - Tokenize trending topics into individual words
   - Filter for "fun words" suitable for Italian brain rot
   - **Question**: What makes a word "fun"? (nouns, adjectives, pop culture terms?)

3. **Random Selection**
   - Randomly select 1-2 tokens from trending list
   - Generate random list of 20 tokens

4. **AI Selection**
   - AI selects best combinations from random list of 20 tokens
   - **Question**: What criteria? (humor potential, viral potential, Italian compatibility?)

## Pipeline 2: Italian Trending Topics + Pairing

### Steps:
1. **Query Google BigQuery** for Italian trending topics
   - **Question**: Same dataset but filtered by country=Italy?
   - **Output**: List of Italian trending topics

2. **Tokenize Italian Words**
   - Extract Italian words from trending topics
   - Generate short Italian phrases (20 words randomly from Italian topics)

3. **Compare with American Trends**
   - Take 20 words from American trending topics
   - Compare with 20 Italian words/phrases

4. **AI Pairing**
   - AI identifies 2-3 objects from American trends that pair well with Italian phrases
   - Creates humorous combinations:
     - Short abbreviations
     - Wordplay
     - Italian phrases + American objects
   - **Output**: List of 2-3 objects paired with Italian sayings/phrases

## Image Generation

### Input:
- Paired lists (2-3 objects + Italian phrases)

### Output:
- Sensational viral images of Italian brain rot
- **Question**: Use existing Midjourney integration or another service?

## Technical Stack

### Required Integrations:
1. **Google BigQuery**
   - Query trending topics (US and Italy)
   - **Question**: Do you have BigQuery access? Which project/dataset?

2. **Google Trends API**
   - Search and validate trending topics
   - **Note**: Google Trends doesn't have official API; may need pytrends library

3. **AI Model**
   - For selection and pairing logic
   - **Question**: OpenAI? Anthropic? Vertex AI?

4. **Image Generation**
   - Midjourney (existing integration) or alternative
   - **Question**: Use existing Midjourney integration?

5. **GCS Storage**
   - Store all intermediate and final outputs
   - Bucket: `brainrot-trends`

## Workflow Questions

1. **Frequency**: How often should this run?
   - Daily? Hourly? On-demand?

2. **Output Format**: 
   - JSON? CSV? Both?
   - Where should results be stored? (GCS, local files, database?)

3. **Italian Language**:
   - Standard Italian or regional variations?
   - Any specific dialect preferences?

4. **"Fun Words" Definition**:
   - What makes a word suitable for Italian brain rot?
   - Should we filter by part of speech (nouns, adjectives)?
   - Any blacklist/whitelist?

5. **AI Selection Criteria**:
   - What makes a combination "best"?
   - Humor score? Viral potential? Cultural relevance?

6. **Image Prompt Format**:
   - How should the final prompts be formatted for image generation?
   - Any specific Midjourney parameters?

## Next Steps

1. ✅ Create GCS bucket structure
2. ✅ Research BigQuery datasets for trending topics
3. ✅ Set up Google Trends integration (pytrends)
4. ✅ Implement tokenization pipeline
5. ✅ Build AI selection/pairing logic
6. ✅ Integrate with image generation
7. ✅ Create orchestration workflow

## Implementation Status

✅ **COMPLETE** - All core components implemented:

- ✅ `scripts/brainrot/config.py` - Centralized configuration
- ✅ `scripts/brainrot/query_bigquery_trends.py` - BigQuery integration
- ✅ `scripts/brainrot/pytrends_fallback.py` - Pytrends fallback
- ✅ `scripts/brainrot/tokenize_trends.py` - Tokenization with profanity filtering
- ✅ `scripts/brainrot/ai_pairing.py` - Gemini-powered pairing
- ✅ `scripts/brainrot/generate_images.py` - Midjourney integration
- ✅ `scripts/brainrot/main_pipeline.py` - Main orchestration
- ✅ `scripts/brainrot/README.md` - Documentation
- ✅ `scripts/brainrot/create_gcs_structure.py` - GCS bucket setup
- ✅ `tests/test_brainrot.py` - Comprehensive test suite (38 tests)
- ✅ `tests/brainrot/README.md` - Test documentation

### Usage

```bash
# Run complete pipeline
python scripts/brainrot/main_pipeline.py

# Skip image generation
python scripts/brainrot/main_pipeline.py --skip-images

# Custom time range
python scripts/brainrot/main_pipeline.py --weeks 2
```

### Dependencies Added

- `pytrends>=4.9.2` - Google Trends API
- `better-profanity>=0.7.0` - Profanity filtering
- `nltk>=3.8.1` - Natural language processing
- `google-cloud-bigquery>=3.13.0` - BigQuery client

### Recent Bug Fixes (20+ Errors Fixed)

**Security & Robustness:**
- ✅ Parameterized BigQuery queries (SQL injection prevention)
- ✅ Safe attribute access for BigQuery rows
- ✅ Empty list/data validation throughout
- ✅ Type checking and structure validation

**API Compatibility:**
- ✅ Fixed pytrends country code mapping
- ✅ DataFrame null/empty checks
- ✅ Profanity filter API fallbacks
- ✅ NLTK data auto-download handling

**Code Quality:**
- ✅ Fixed dataclass mutable defaults
- ✅ Consistent directory naming (`us_trends`)
- ✅ Removed redundant imports
- ✅ Improved error messages

See `scripts/brainrot/README.md` for complete changelog.

### Testing

**Comprehensive test suite added:**
- ✅ `tests/test_brainrot.py` - 38 tests covering all modules
- ✅ Configuration tests
- ✅ BigQuery integration tests (mocked)
- ✅ Pytrends fallback tests (mocked)
- ✅ Tokenization and filtering tests
- ✅ AI pairing logic tests
- ✅ Image generation tests (mocked)
- ✅ Pipeline orchestration tests
- ✅ Edge cases and error handling tests

**Run tests:**
```bash
# Run all brainrot tests
pytest tests/test_brainrot.py -v

# Run with coverage
pytest tests/test_brainrot.py --cov=scripts.brainrot --cov-report=html
```

See `tests/brainrot/README.md` for detailed test documentation.

## Files to Create

- `scripts/brainrot/create_gcs_structure.py` - Set up bucket directories
- `scripts/brainrot/query_bigquery_trends.py` - Query trending topics
- `scripts/brainrot/tokenize_trends.py` - Tokenization logic
- `scripts/brainrot/ai_pairing.py` - AI selection and pairing
- `scripts/brainrot/generate_images.py` - Image generation orchestration
- `scripts/brainrot/main_pipeline.py` - Main orchestration script

