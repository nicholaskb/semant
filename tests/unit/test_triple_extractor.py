import pytest

import utils.triple_extractor as te

extract_triples = te.extract_triples

# Skip entire module if spaCy unavailable and fallback may vary
if te._NLP is None:
    pytest.skip("spaCy not available – skipping detailed extractor tests", allow_module_level=True)

SAMPLES = [
    ("Alice eats apples.", {("Alice", "eat", "apples")}),
    ("Bob wrote code.", {("Bob", "write", "code")}),
    ("The cat chased the mouse", {("cat", "chase", "mouse")}),
]


@pytest.mark.parametrize("text,expected", SAMPLES)
def test_extract_triples(text, expected):
    triples = set(extract_triples(text))
    norm = set((s.lower(), p.lower(), o.lower()) for s, p, o in triples)
    exp_norm = set((s.lower(), p.lower(), o.lower()) for s, p, o in expected)
    assert exp_norm & norm, f"Expected triple not found. got {norm}" 