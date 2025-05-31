# Main Chain Execution Guide

This README was authored by another agent to document how to run the main agent chain. The script processes a user question through multiple agents sequentially and prints a final JSON result.

## Running the Main Chain

Use the `run_main_chain.py` script from the `scripts/` directory:

```bash
python scripts/run_main_chain.py "Is AI useful in diagnosing rare diseases?"
```

The script loads all available agent personas defined in `main.py`, executes the chain with verbose output, and prints the final response in JSON format.

## Prerequisites

Ensure you have installed the repository dependencies:

```bash
pip install -r requirements.txt
```

Initialize the knowledge graph if you haven't done so:

```bash
python scripts/init_kg.py
```

## Expected Output

Running the script produces a series of log messages showing each agent's action, followed by a JSON object summarizing the response from the entire chain.

