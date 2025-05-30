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
