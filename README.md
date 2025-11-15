# Ticketing-Agent

> A lightweight local agent framework for interacting with ticketing systems (Zammad) and running subagents for classification, creation, search, and update of tickets.

## Overview

This repository contains a modular ticketing assistant built in Python. The main code lives under the `ticketing` package and includes:

- `ticketing/agent.py` — main agent/controller logic.
- `ticketing/subagents/` — orchestrator and subagent code for classification, creation, search, and update.
- `ticketing/custom_utils/` — environment interaction helpers and prompt templates.
- `ticketing/tools/zammad_client.py` — helper for interacting with Zammad (or other ticketing backends).

There are example YAML agent definitions in `ticketing/tmp/ticketing/` used for local orchestrations.

## Requirements

- Python 3.10+ (this project was developed with Python 3.10)
- Windows (development environment provided under `venv-windows/`) — instructions below show PowerShell commands.

Install dependencies:

```powershell
# Activate the provided virtual environment (PowerShell)
.\venv-windows\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

If you prefer to create a dedicated venv instead of the included `venv-windows`, create and activate one then install requirements.

## Environment

- There is a `.env` file inside the `ticketing/` folder. Populate it with your credentials and any required configuration for the Zammad client or other integrations before running the agent.

Common env items (example keys — adapt to your environment):

- `ZAMMAD_URL`
- `ZAMMAD_USER`
- `ZAMMAD_TOKEN`

## Quick start

1. Activate virtual environment (see above).
2. Ensure `ticketing/.env` is configured.
3. Run the main agent entrypoint:

```powershell
python -m ticketing.agent
# or
python ticketing\agent.py
```

Note: depending on how your environment and prompts are configured, the agent may start in an interactive mode or run orchestrations defined by local YAML files in `ticketing/tmp/ticketing/`.

## Project structure (high level)

- `ticketing/` — main package with agents, prompts, and utilities
  - `custom_utils/` — helpers and environment interactions
  - `prompts/` — prompt templates used by agents
  - `subagents/` — subagent implementations and orchestrator
  - `tmp/ticketing/` — example YAML agent configs and dumps
- `tools/` — reusable tooling like `zammad_client.py`
- `venv-windows/` — included virtual environment (Windows)

## Development notes

- Prompts live in `ticketing/custom_utils/prompts` and can be updated to improve agent behaviour.
- No automated tests are included by default; add unit tests under a `tests/` directory if needed.

## Next steps / Suggestions

- Verify and secure secrets in `ticketing/.env` before connecting to live systems.
- If you want, I can:
  - Add a small runnable example that creates a ticket against a test Zammad instance.
  - Add a `Makefile` / PowerShell script for common tasks (setup, run).
  - Commit `README.md` and push the change.

If you'd like me to commit and push the README or make any edits to the content, tell me how you want it phrased.
