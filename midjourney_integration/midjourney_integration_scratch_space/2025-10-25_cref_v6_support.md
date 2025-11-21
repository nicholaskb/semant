# 2025-10-25 — Add --cref/--cw V6 Support and Auto-Version Detection

- **Timestamp**: 2025-10-25 12:00
- **Objective**: Fix error "Invalid parameter `--cref` is not compatible with `--version 7`" by adding proper V6 parameter extraction and auto-version detection

## Files Changed

1. **`main.py`** (endpoint `POST /api/midjourney/imagine`):
   - Extract `--cref <url>` and `--cw <int>` from prompts (lines 900-903)
   - Remove these parameters from prompt text to avoid GoAPI errors (lines 913-916)
   - Auto-detect and set `model_version="v6"` when --cref/--cw present (lines 937-939)
   - Pass `cref_url` and `cref_weight` to client.submit_imagine (lines 964-965)
   - Include cref parameters in KG logging (lines 992-993)

2. **`midjourney_integration/client.py`**:
   - Add `cref_url` and `cref_weight` parameters to submit_imagine signature (lines 145-146)
   - Prefix prompt with "image" when starting with --cref or --oref (line 154)
   - Add cref/cw to payload when present (lines 179-182)

## Endpoints Affected
- `POST /api/midjourney/imagine`: Now properly handles both V6 (--cref/--cw) and V7 (--oref/--ow) parameters

## Implementation Details

### Version Detection Logic
1. Extract reference parameters BEFORE prompt sanitization
2. Priority order for version determination:
   - Explicit version from form/API parameter
   - Version flag in prompt (--v 6, --v 7)
   - Auto-detect V7 if --oref/--ow present
   - Auto-detect V6 if --cref/--cw present
   - Default to unspecified (GoAPI will use its default)

### Parameter Extraction Pattern
```python
# V6 parameters
cref_match = re.search(r"--cref\s+(\S+)", prompt)
cw_match = re.search(r"--cw\s+(\d+)", prompt)

# V7 parameters  
oref_match = re.search(r"--oref\s+(\S+)", prompt)
ow_match = re.search(r"--ow\s+(\d+)", prompt)
```

## Verification Steps

1. **Test V6 with --cref**:
   ```bash
   curl -X POST http://localhost:8080/api/midjourney/imagine \
     -F "prompt=colorful portrait --cref https://example.com/face.jpg --cw 100" \
     -F "process_mode=turbo"
   ```
   - Should auto-set version to V6
   - Payload should contain `input.cref` and `input.cw`
   - No "incompatible with version 7" error

2. **Test V7 with --oref**:
   ```bash
   curl -X POST http://localhost:8080/api/midjourney/imagine \
     -F "prompt=sunset scene --oref https://example.com/object.jpg --ow 75" \
     -F "process_mode=turbo"
   ```
   - Should auto-set version to V7
   - Payload should contain `input.oref` and `input.ow`

3. **Test explicit version override**:
   ```bash
   curl -X POST http://localhost:8080/api/midjourney/imagine \
     -F "prompt=test prompt --cref https://example.com/face.jpg" \
     -F "version=v6"
   ```
   - Should use explicitly specified V6

## Implemented vs Proposed
- **Implemented**: Full support for V6 --cref/--cw parameters with auto-version detection
- **Proposed**: Consider adding client-side validation to warn users before submission when mixing incompatible parameters
- **Future**: Add validation to prevent --cref on V7 and --oref on V6 at the client level

## Error Resolution
This fix resolves the error:
```json
{
  "error": "Invalid parameter\n`--cref` is not compatible with `--version 7`"
}
```

By automatically detecting --cref usage and setting the appropriate V6 version, preventing version mismatch errors.

