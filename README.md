# Multi-Agent Knowledge Coordination Challenge

This repository contains a minimal implementation of a small multi-agent system. The example is inspired by the provided data challenge instructions.

Five simple agents coordinate to answer a single question about the usefulness of AI in diagnosing rare diseases. Each agent performs a single step and logs its actions. The process is orchestrated by the `run_swarm` function in `main.py`.

## Running

Execute the script with Python:

```bash
python3 main.py
```

It will print a JSON report containing the summary, pros, cons, and a log of each agent's actions.

Example output:

```json
{
  "summary": "AI shows promise in diagnosing rare diseases by analyzing large datasets and highlighting subtle patterns. However, its effectiveness depends on high-quality data and careful validation to avoid mistakes.",
  "pros": [
    "Scales expertise across many hospitals",
    "Finds patterns humans might miss"
  ],
  "cons": [
    "Requires high-quality labeled data",
    "Potential for false positives or misdiagnosis"
  ],
  "log": [
    {"agent": "TaskPlanner", "action": "Delegated task to Researcher"},
    {"agent": "Researcher", "output": ["AI can analyze large datasets of medical records to uncover rare disease patterns.", "Machine learning models have been used to assist doctors in diagnosing conditions with few existing cases.", "Access to specialized AI tools can be limited in under-resourced regions."]},
    {"agent": "Analyst", "pros": ["Scales expertise across many hospitals", "Finds patterns humans might miss"], "cons": ["Requires high-quality labeled data", "Potential for false positives or misdiagnosis"]},
    {"agent": "Summarizer", "summary": "AI shows promise in diagnosing rare diseases by analyzing large datasets and highlighting subtle patterns. However, its effectiveness depends on high-quality data and careful validation to avoid mistakes."},
    {"agent": "Auditor", "action": "Compiled final report"}
  ]
}
```
