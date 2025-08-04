# Diary Integration Across Agents – Implementation & Review Plan

## 1  Objective
Ensure **every agent** automatically records diary thoughts, persists them to the Knowledge Graph (KG) as both literal text *and* structured triples, and expose those diaries through API & UI for observability.

## 2  Background
* `BaseAgent.write_diary()` already writes a literal entry and corresponding KG blank-node.
* Most concrete agents *never call* this method, and diary literals are not decomposed into triples.
* No public endpoint or UI exists for viewing diary content.

## 3  Implementation Road-Map
| ID | Phase | Task | Key Points | Owner | Deps |
|----|-------|------|-----------|-------|------|
| T1 | P1 |Refactor all agents to subclass `BaseAgent`|Demo/legacy classes in `examples/` need update|Core team|–|
| T2 | P1 |Add **auto-diary hooks** inside `BaseAgent.process_message()`|Log **RECV** & **SEND** with details; toggle via `auto_diary` flag|Core team|T1|
| T3 | P2 |Implement `utils/triple_extractor.py`|Initial spaCy heuristic, future LLM drop-in|KG team|T2|
| T4 | P2 |Extend `write_diary` to run extractor & store triples|Use `_add_simple_triple` helper|KG team|T3|
| T5 | P3 |FastAPI endpoints `/diary/{agent}` & `/diary/{agent}/triples`|Read from memory + SPARQL|API team|T4|
| T6 | P3 |React Diary Viewer page|Polling or WebSocket; highlight triples|Frontend team|T5|
| T7 | P1 |CI test `test_all_agents_write_diary`|Ensures at least one entry after ping|QA team|T2|
| T8 | P2 |Unit tests for triple extraction correctness|±95 % precision/recall on sample corpus|QA team|T3|
| T9 | P3 |Security hardening (authN/Z, PII redaction) on diary endpoints|OAuth2 bearer token; redact `details.ssn`|Security team|T5|
| T10| P3 |Performance benchmarking & optimisation|≤5 ms overhead per diary call under load|Perf team|T4|
| T8 | P4 |Docs & README updates|Explain flags, endpoints, SPARQL examples|Docs team|T6|

## Plan Version

**v1.1 – after internal critic review (Architecture, KG, DX, Security, TestCoverage) – {{date}}**

Key changes:
* Added tasks **T9** (Security hardening) & **T10** (Performance benchmarking) per critic feedback.
* Clarified ontology rules for diary-derived triples.
* Documented flag `settings.auto_diary` (default **true**).
* Expanded test requirements to cover triple extraction accuracy.
* Added note on concurrency overhead & async threadpool for NLP.

## 4  Critique & Iterative Review Workflow

1. **Critique Agents** (run sequentially each cycle)
   * **ArchitectureCriticAgent** – codebase impact, coupling, backward-compat.
   * **KnowledgeGraphCriticAgent** – triple design, ontology alignment.
   * **DXCriticAgent** – API ergonomics, config flags, docs clarity.
   * **SecurityCriticAgent** – auth on new endpoints, PII in diary.
   * **TestCoverageCriticAgent** – unit/integration coverage adequacy.

2. **Cycle Steps**
   1. Present *current* plan to next critic.
   2. Critic returns JSON `{score, issues, suggestions, blocking}`.
   3. Update **Plan Version** *(increment minor)*, address blocking IDs.
   4. Repeat until all critics score ≥ 8, **and** no blocking list.

## 5  Deviation Handling
* Any task change ➜ open **Deviation PR** referencing task ID; include rationale & impact matrix.
* Critique agents automatically re-run on the PR diff before merge.
* If deviation invalidates previous approvals (< 8 score) the plan re-enters critique loop.

## 6  Reusable Critique Prompt (copy-paste per agent)
```
You are {{critic_name}}.
Context: Reviewing *Diary Integration Plan* version {{version}} dated {{date}}.

Checklist:
1. Architecture soundness (Y/N + notes)
2. Feasibility of timeline & dependencies (score 1-10)
3. Data model correctness (triples & ontology)
4. Security & privacy concerns listed
5. Test coverage adequate (list missing cases)
6. Documentation clarity (list sections needing work)
7. Overall readiness score (0-10)

Instructions:
• Return JSON with keys `score`, `issues`, `suggestions`, `blocking`.
• Mark blocking tasks by their ID (e.g. "T4").
• Be concise but specific.
```

> Paste this prompt into each critic agent’s `process_message`. Continue critique cycles until criteria in §4 step 2 are met.

---
*Last updated: {{commit_sha}} (v1.1)* 