# Brain Rot Tests

Comprehensive test suite for the Brain Rot project scripts.

## Test Coverage

### Configuration Tests (`TestBrainRotConfig`)
- ✅ Default configuration values
- ✅ `__post_init__` mutable defaults
- ✅ Custom configuration values

### BigQuery Tests (`TestBigQueryTrendsQuery`)
- ✅ Client initialization
- ✅ Successful query execution
- ✅ Empty result handling
- ✅ GCS save functionality

### Pytrends Tests (`TestPytrendsTrendsQuery`)
- ✅ Client initialization (when available)
- ✅ Trending topics retrieval
- ✅ Empty DataFrame handling
- ✅ Fallback mechanisms

### Tokenization Tests (`TestTrendTokenizer`)
- ✅ Initialization
- ✅ Empty trends handling
- ✅ Basic tokenization
- ✅ Length filtering
- ✅ Profanity filtering
- ✅ Token deduplication

### AI Pairing Tests (`TestAIPairingEngine`)
- ✅ Initialization
- ✅ Empty token handling
- ✅ Fallback combinations
- ✅ Prompt creation
- ✅ JSON parsing (valid/invalid)
- ✅ Combined prompt generation

### Image Generation Tests (`TestImageGenerator`)
- ✅ Initialization
- ✅ Empty combinations handling
- ✅ Invalid combo handling
- ✅ Prompt creation
- ✅ Prompt enhancement

### Pipeline Tests (`TestBrainRotPipeline`)
- ✅ Initialization
- ✅ Step 1: Query trends
- ✅ Step 2: Tokenize
- ✅ Step 3: AI pairing

### Edge Cases (`TestEdgeCases`)
- ✅ Empty configurations
- ✅ Empty strings
- ✅ Single token scenarios

## Running Tests

### Run All Brain Rot Tests
```bash
pytest tests/test_brainrot.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_brainrot.py::TestBrainRotConfig -v
pytest tests/test_brainrot.py::TestTrendTokenizer -v
```

### Run Specific Test
```bash
pytest tests/test_brainrot.py::TestBrainRotConfig::test_config_defaults -v
```

### Run with Coverage
```bash
pytest tests/test_brainrot.py --cov=scripts.brainrot --cov-report=html
```

## Test Requirements

Tests use mocking for external services:
- **BigQuery**: Mocked via `unittest.mock`
- **Pytrends**: Mocked (skipped if library unavailable)
- **Vertex AI**: Mocked (no actual API calls)
- **Midjourney**: Mocked (no actual API calls)
- **GCS**: Mocked (no actual storage operations)

## Notes

- Tests are designed to run without external dependencies
- All external API calls are mocked
- Tests verify logic, error handling, and data validation
- Integration tests require full environment setup (not included in unit tests)

## Future Enhancements

- [ ] Add integration tests with real services (optional)
- [ ] Add performance benchmarks
- [ ] Add stress tests for large datasets
- [ ] Add tests for GCS structure creation
- [ ] Add tests for error recovery scenarios

