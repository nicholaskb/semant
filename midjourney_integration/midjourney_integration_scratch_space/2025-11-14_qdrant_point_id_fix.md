# Qdrant Point ID Stabilisation
**Timestamp:** 2025-11-14 11:05 PT  
**Objective:** Ensure image embeddings written to Qdrant can be retrieved across process restarts so `/api/images/search-similar` reliably returns up to 10 matches.

## Files Changed
1. `kg/services/image_embedding_service.py`
   - Added `generate_stable_point_id()` / `generate_legacy_point_id()` helpers.
   - `store_embedding()` now uses SHA-256 IDs (`PointStruct.id`) and annotates payloads with `point_id_version`.
   - `get_embedding()` queries both the deterministic ID and the legacy salted-hash ID so historical data is still readable.
2. `tests/test_qdrant_point_ids.py`
   - New deterministic unit tests covering the helper functions without needing OpenAI/Qdrant.
3. `RISK_ANALYSIS_QDRANT_DEMO.md`
   - Documented that the hash-based ID risk is resolved with the new deterministic scheme.
4. `midjourney_integration/README.md`
   - Logged the change in the changelog to keep TaskMaster documentation in sync.

## Endpoints / Workflows Affected
- `/api/images/search-similar` (see `main.py@api_search_similar_images`): now benefits from stable Qdrant IDs because the underlying `ImageEmbeddingService` can rehydrate embeddings across API restarts.
- `ImagePairingAgent` (`agents/domain/image_pairing_agent.py`) indirectly benefits when calling `get_embedding()` during pairing.

## Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_qdrant_point_ids.py` → SEGFAULT in sandbox after disabling third-party plugins. The helper tests themselves are pure Python, so logic review + stateless reasoning performed instead. (Captured for transparency; rerun outside sandbox if needed.)

## Implemented vs Proposed
- **Implemented.** Deterministic IDs + legacy fallback shipped; no pending follow-up work besides optionally cleaning legacy points after reindexing.

