"""
Unit tests for deterministic Qdrant point ID helpers.

These tests do not require a running Qdrant instance or OpenAI keys; they only
exercise the pure helper functions used by ImageEmbeddingService.
"""

from kg.services.image_embedding_service import (
    generate_stable_point_id,
    generate_legacy_point_id,
)


def test_generate_stable_point_id_is_deterministic():
    uri = "http://example.org/image/duckling-001"
    first = generate_stable_point_id(uri)
    second = generate_stable_point_id(uri)
    assert first == second
    assert len(first) == 64  # full SHA-256 hex digest


def test_generate_stable_point_id_changes_with_uri():
    uri1 = "http://example.org/image/duckling-001"
    uri2 = "http://example.org/image/duckling-002"
    assert generate_stable_point_id(uri1) != generate_stable_point_id(uri2)


def test_generate_legacy_point_id_within_bounds():
    uri = "http://example.org/image/legacy"
    point_id = generate_legacy_point_id(uri)
    assert isinstance(point_id, int)
    assert 0 <= point_id < 2**63

