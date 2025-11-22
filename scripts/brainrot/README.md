# Brain Rot Project

Generate viral "Italian brain rot" content by combining trending Italian phrases with trending American objects.

## Overview

This project creates humorous, viral-worthy image prompts by:
1. **Querying trending topics** from Google BigQuery and Google Trends (US and Italy)
2. **Tokenizing and filtering** words (nouns/verbs, profanity filtering, length limits)
3. **AI-powered pairing** using Gemini to select best combinations
4. **Generating images** using Midjourney integration

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install pytrends better-profanity nltk google-cloud-bigquery

# Download NLTK data (will auto-download on first run)
python -c "import nltk; nltk.download('punkt'); nltk.download('averaged_perceptron_tagger'); nltk.download('stopwords')"
```

### Environment Variables

```bash
# Google Cloud
export GOOGLE_PROJECT_ID="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

# Midjourney (optional, for image generation)
export MIDJOURNEY_API_TOKEN="your-token"
```

### Run Pipeline

```bash
# Run complete pipeline
python scripts/brainrot/main_pipeline.py

# Skip image generation
python scripts/brainrot/main_pipeline.py --skip-images

# Custom time range (weeks)
python scripts/brainrot/main_pipeline.py --weeks 2
```

## Configuration

All parameters are in `scripts/brainrot/config.py`:

- **Time Range**: `time_range_weeks` (default: 1 week)
- **Regions**: `pytrends_regions` (default: ["US", "IT"])
- **Token Filters**: `min_word_length`, `max_word_length`, `filter_profanity`
- **AI Model**: `ai_model` (default: "gemini-1.5-flash")
- **Combinations**: `combinations_per_run` (default: 15)
- **Image Style**: `image_style`, `aspect_ratio`, `variations_per_combination`

## Pipeline Steps

### Step 1: Query Trending Topics
```bash
python scripts/brainrot/query_bigquery_trends.py
# Falls back to pytrends if BigQuery unavailable
python scripts/brainrot/pytrends_fallback.py
```

### Step 2: Tokenize Trends
```bash
python scripts/brainrot/tokenize_trends.py
```

### Step 3: AI Pairing
```bash
python scripts/brainrot/ai_pairing.py
```

### Step 4: Generate Images
```bash
python scripts/brainrot/generate_images.py
```

## Output Structure

All outputs are stored in GCS bucket `brainrot-trends`:

```
brainrot-trends/
├── us_trends/
│   ├── raw/              # Raw BigQuery/pytrends results
│   └── tokenized/        # Tokenized words
├── italian_trends/
│   ├── raw/              # Raw BigQuery/pytrends results
│   └── tokenized/        # Tokenized words
├── combinations/
│   ├── ai_selections/    # AI-paired combinations
│   └── final/            # Finalized prompts
└── generated_images/      # Image generation logs
```

## Features

- ✅ **BigQuery Integration**: Query public Google Trends datasets
- ✅ **Pytrends Fallback**: Use pytrends when BigQuery unavailable
- ✅ **Smart Tokenization**: NLTK-based POS tagging, profanity filtering
- ✅ **AI Pairing**: Gemini-powered selection of viral combinations
- ✅ **Image Generation**: Midjourney integration for viral images
- ✅ **GCS Storage**: All data stored in Google Cloud Storage
- ✅ **Parameterized**: All settings configurable via `config.py`

## Research-Based Viral Content Criteria

The AI pairing engine uses research-backed criteria for selecting combinations:

1. **Humor Potential**: Unexpected, absurd juxtapositions
2. **Viral Potential**: Meme-worthy, shareable content
3. **Cultural Contrast**: Amusing Italian-American differences
4. **Visual Potential**: Compelling image/meme material
5. **Simplicity**: Easy to understand and remember

## Troubleshooting

### BigQuery Errors
- Ensure `GOOGLE_PROJECT_ID` is set
- Verify BigQuery API is enabled
- Check service account permissions

### Pytrends Rate Limits
- Pytrends has strict rate limits (1-2 requests per second)
- Scripts include automatic rate limiting
- If errors persist, wait 5-10 minutes between runs

### NLTK Data Missing
- Scripts auto-download required NLTK data
- If issues persist: `python -m nltk.downloader all`

### Midjourney Errors
- Verify `MIDJOURNEY_API_TOKEN` is set
- Check API quota/limits
- Use `--skip-images` to test pipeline without image generation

## Examples

### Example Combination Output

```json
{
  "american_objects": ["iPhone", "Starbucks"],
  "italian_phrases": ["mamma mia"],
  "explanation": "Classic Italian exclamation with modern American tech - absurdly relatable",
  "humor_score": 8,
  "viral_score": 9,
  "combined_prompt": "mamma mia with iPhone, Starbucks"
}
```

### Example Image Prompt

```
mamma mia with iPhone, Starbucks, meme-style, surreal, vibrant colors, high quality, viral meme style, trending on social media, absurdist humor, colorful and eye-catching, close-up shot
```

## Next Steps

1. **Monitor Results**: Check GCS bucket for generated combinations
2. **Refine Prompts**: Adjust `config.py` based on results
3. **Scale Up**: Increase `combinations_per_run` for more output
4. **A/B Test**: Try different image styles and aspect ratios

## Recent Updates & Bug Fixes

### Security & Robustness Improvements (Latest)

**20+ errors fixed across all modules:**

1. **Security**
   - ✅ Parameterized BigQuery queries to prevent SQL injection
   - ✅ Safe attribute access using `getattr()` for BigQuery rows

2. **Data Validation**
   - ✅ Empty list checks before `random.sample()` calls
   - ✅ Type validation for dictionaries and lists throughout
   - ✅ JSON parsing error handling with fallbacks

3. **API Compatibility**
   - ✅ Fixed `pytrends` country code mapping (`pn` parameter)
   - ✅ Added DataFrame null/empty checks for pytrends responses
   - ✅ Profanity filter API fallback handling (multiple methods)

4. **Error Handling**
   - ✅ NLTK data auto-download with proper error handling
   - ✅ Improved error messages for missing data
   - ✅ Try/except blocks for all external API calls

5. **Configuration**
   - ✅ Fixed dataclass mutable default arguments (using `__post_init__`)
   - ✅ Consistent directory naming (`us_trends` vs `american_trends`)

6. **Code Quality**
   - ✅ Removed redundant imports
   - ✅ Fixed typos (`PYTENDS_AVAILABLE` → `PYTRENDS_AVAILABLE`)
   - ✅ Improved prompt generation with empty list handling

**Files Updated:**
- `config.py` - Fixed dataclass initialization
- `query_bigquery_trends.py` - Parameterized queries, safe attribute access
- `pytrends_fallback.py` - Fixed API usage, DataFrame handling
- `tokenize_trends.py` - NLTK downloads, profanity fallbacks, word filtering
- `ai_pairing.py` - Empty list handling, validation, type conversion
- `generate_images.py` - Type validation, prompt enhancement
- `main_pipeline.py` - Import cleanup, data validation
- `create_gcs_structure.py` - Exception handling, directory naming

## Testing

Comprehensive test suite available in `tests/test_brainrot.py`:

```bash
# Run all brainrot tests
pytest tests/test_brainrot.py -v

# Run with coverage
pytest tests/test_brainrot.py --cov=scripts.brainrot --cov-report=html

# Run specific test class
pytest tests/test_brainrot.py::TestTrendTokenizer -v
```

**Test Coverage:**
- ✅ Configuration validation
- ✅ BigQuery integration (mocked)
- ✅ Pytrends fallback (mocked)
- ✅ Tokenization and filtering
- ✅ AI pairing logic
- ✅ Image generation (mocked)
- ✅ Pipeline orchestration
- ✅ Edge cases and error handling

See `tests/brainrot/README.md` for detailed test documentation.

## Notes

- BigQuery public datasets may have schema variations - adjust queries as needed
- Pytrends is unofficial and may break - BigQuery is preferred
- Image generation requires Midjourney API access
- All profanity filtering uses `better-profanity` library
- All scripts now include comprehensive error handling and validation

