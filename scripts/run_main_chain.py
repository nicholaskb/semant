import argparse
import json
from main import run_swarm, AGENT_PERSONAS


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the main agent chain")
    parser.add_argument("question", help="User question to pass to the agent chain")
    args = parser.parse_args()

    agents = list(AGENT_PERSONAS.keys())
    result = run_swarm(
        task=args.question,
        agents=agents,
        personas=AGENT_PERSONAS,
        verbose=True,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
