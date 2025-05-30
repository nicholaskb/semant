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
