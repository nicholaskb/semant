# semant
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
    {"agent": "Researcher", "output": [
      "AI can analyze large datasets of medical records to uncover rare disease patterns.",
      "Machine learning models have been used to assist doctors in diagnosing conditions with few existing cases.",
      "Access to specialized AI tools can be limited in under-resourced regions."
    ]},
    {"agent": "Analyst", "pros": [
      "Scales expertise across many hospitals",
      "Finds patterns humans might miss"
    ], "cons": [
      "Requires high-quality labeled data",
      "Potential for false positives or misdiagnosis"
    ]},
    {"agent": "Summarizer", "summary": "AI shows promise in diagnosing rare diseases by analyzing large datasets and highlighting subtle patterns. However, its effectiveness depends on high-quality data and careful validation to avoid mistakes."},
    {"agent": "Auditor", "action": "Compiled final report"}
  ]
}
```

main.py
New
+114
-0

# A simple implementation of the Multi-Agent Knowledge Coordination Challenge
# This script defines minimal agent behaviors and uses a lightweight
# `run_swarm` helper to coordinate them and produce a structured result.

from __future__ import annotations

from typing import Dict, List, Callable, Any

from swarm.swarm import run_swarm


# Agent function type
AgentFn = Callable[[str, Dict[str, Any]], str]


def task_planner(task: str, state: Dict[str, Any]) -> str:
    """Break down the task and delegate to Researcher."""
    log_entry = {
        "agent": "TaskPlanner",
        "action": "Delegated task to Researcher",
    }
    state.setdefault("log", []).append(log_entry)
    state["current_task"] = task
    return task


def researcher(task: str, state: Dict[str, Any]) -> str:
    """Return three mock facts about the topic."""
    facts = [
        "AI can analyze large datasets of medical records to uncover rare disease patterns.",
        "Machine learning models have been used to assist doctors in diagnosing conditions with few existing cases.",
        "Access to specialized AI tools can be limited in under-resourced regions.",
    ]
    state["facts"] = facts
    state.setdefault("log", []).append({"agent": "Researcher", "output": facts})
    return " ".join(facts)


def analyst(_: str, state: Dict[str, Any]) -> str:
    """Convert facts into pros and cons."""
    facts = state.get("facts", [])
    pros = [
        "Scales expertise across many hospitals",
        "Finds patterns humans might miss",
    ]
    cons = [
        "Requires high-quality labeled data",
        "Potential for false positives or misdiagnosis",
    ]
    state["pros"] = pros
    state["cons"] = cons
    state.setdefault("log", []).append({"agent": "Analyst", "pros": pros, "cons": cons})
    return "analysis complete"


def summarizer(_: str, state: Dict[str, Any]) -> str:
    pros = state.get("pros", [])
    cons = state.get("cons", [])
    summary = (
        "AI shows promise in diagnosing rare diseases by analyzing large datasets and highlighting subtle patterns. "
        "However, its effectiveness depends on high-quality data and careful validation to avoid mistakes."
    )
    state["summary"] = summary
    state.setdefault("log", []).append({"agent": "Summarizer", "summary": summary})
    return summary


def auditor(_: str, state: Dict[str, Any]) -> str:
    log = state.get("log", [])
    result = {
        "summary": state.get("summary", ""),
        "pros": state.get("pros", []),
        "cons": state.get("cons", []),
        "log": log,
    }
    state["result"] = result
    # final log
    state.setdefault("log", []).append({"agent": "Auditor", "action": "Compiled final report"})
    return "audit complete"


AGENT_FUNCS: Dict[str, AgentFn] = {
    "TaskPlanner": task_planner,
    "Researcher": researcher,
    "Analyst": analyst,
    "Summarizer": summarizer,
    "Auditor": auditor,
}


AGENT_PERSONAS = {
    "TaskPlanner": "You divide the task into subtasks and assign them. Start by passing it to Researcher.",
    "Researcher": "You find 3 relevant facts about the topic from mock sources.",
    "Analyst": "You review the facts and extract pros and cons.",
    "Summarizer": "You write a concise summary of the analyst's findings.",
    "Auditor": "You validate the process, log agent steps, and produce a final JSON report.",
}

TASK = "Is AI useful in diagnosing rare diseases? Create a brief summary with pros and cons."

agents = list(AGENT_PERSONAS.keys())

if __name__ == "__main__":
    result = run_swarm(
        task=TASK,
        agents=agents,
        personas=AGENT_PERSONAS,
        max_turns=12,
        verbose=True,
        output_format="json",
        agent_funcs=AGENT_FUNCS,
    )
    import json
    print(json.dumps(result, indent=2))
swarm/__init__.py

No content
swarm/swarm.py
New
+39
-0

from typing import Dict, List, Any, Callable

AgentFn = Callable[[str, Dict[str, Any]], str]


def run_swarm(task: str, agents: List[str], personas: Dict[str, str], max_turns: int = 12,
              verbose: bool = True, output_format: str = "json",
              agent_funcs: Dict[str, AgentFn] | None = None) -> Dict[str, Any]:
    """A very small stand-in for the OpenAI Swarm `run_swarm` helper.

    Args:
        task: The initial task for the agents.
        agents: Ordered list of agent names.
        personas: Mapping of agent names to persona descriptions.
        max_turns: Unused; included for compatibility with the real API.
        verbose: Whether to print progress messages.
        output_format: Currently always 'json'.
        agent_funcs: Optional mapping of agent names to callable functions. If
            omitted, agents must implement their behavior elsewhere.

    Returns:
        The final state dictionary produced by the last agent.
    """
    if agent_funcs is None:
        raise ValueError("agent_funcs mapping is required for this minimal stub")

    state: Dict[str, Any] = {}
    message = task
    for agent_name in agents:
        fn = agent_funcs.get(agent_name)
        if not fn:
            continue
        if verbose:
            print(f"[{agent_name}] processing...")
        message = fn(message, state)

    if verbose:
        print("Final state:", state.get("result"))
    return state.get("result", {})
