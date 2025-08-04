"""utils.triple_extractor

Light-weight subject-verb-object triple extractor for diary sentences (T3).

Design goals:
• **Zero-config**: attempts to import spaCy; if unavailable, falls back to a naive regex/heuristic so prod code never breaks.
• **Pure-python** fallback keeps external dependencies optional.
• **Deterministic**: returns list[tuple[str,str,str]] for each sentence.
• **Safe for async** callers – CPU-bound; run in executor if heavy.
"""

from __future__ import annotations

import re
from typing import List, Tuple

__all__ = ["extract_triples"]

# ---------------------------------------------------------------------------
# Helper – spaCy optional
# ---------------------------------------------------------------------------
try:
    import spacy

    _NLP = spacy.load("en_core_web_sm", disable=["ner", "textcat"])  # small & fast
except Exception:  # pragma: no cover – ensures fallback during tests w/o spacy
    _NLP = None


# ---------------------------------------------------------------------------
# Fallback regex patterns (very naive – best-effort)
# ---------------------------------------------------------------------------
# Matches simple "Alice eats apples" → (Alice, eats, apples)
_SIMPLE_SVO = re.compile(r"(?P<s>\b\w+\b)\s+(?P<v>\b\w+\b)s?\s+(?P<o>\b\w+\b)")


def _heuristic_extract(sentence: str) -> List[Tuple[str, str, str]]:
    """Naive regex-based SVO extractor as ultimate fallback."""
    m = _SIMPLE_SVO.search(sentence)
    if not m:
        return []
    subj, verb, obj = m.group("s"), m.group("v"), m.group("o")
    # crude lemmatization for common English verb suffixes
    original = verb.lower()
    lemma = re.sub(r"(ed|es|s)$", "", original)
    triples = [(subj, original, obj)]
    if lemma != original and len(lemma) > 2:
        triples.append((subj, lemma, obj))
    return triples


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_triples(text: str) -> List[Tuple[str, str, str]]:
    """Return list of (subject, predicate, object) triples extracted from *text*.

    If spaCy is available, use dependency parse for better accuracy; otherwise
    fall back to `_heuristic_extract` per sentence.
    """
    triples: List[Tuple[str, str, str]] = []

    if not text:
        return triples

    if _NLP is None:
        # Fallback – split on punctuation & newlines
        for sent in re.split(r"[.!?\n]+", text):
            sent = sent.strip()
            if not sent:
                continue
            triples.extend(_heuristic_extract(sent))
        return triples

    # spaCy path – lightweight, disable heavy pipeline components
    doc = _NLP(text)

    for sent in doc.sents:
        subj_tokens = [t for t in sent if t.dep_ in ("nsubj", "nsubjpass")]
        verb_tokens = [t for t in sent if t.pos_ == "VERB"]
        obj_tokens = [t for t in sent if t.dep_ in ("dobj", "pobj", "attr")]

        if subj_tokens and verb_tokens and obj_tokens:
            subj = subj_tokens[0].text
            verb = verb_tokens[0].lemma_  # canonical verb
            obj = obj_tokens[0].text
            triples.append((subj, verb, obj))

    return triples 