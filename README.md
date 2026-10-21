## Mini-Agent

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![OpenAI SDK](https://img.shields.io/badge/OpenAI-Responses%20API-green.svg)](https://platform.openai.com/docs/guides/tools)
[![uv](https://img.shields.io/badge/uv-package%20manager-de5fe9.svg)](https://docs.astral.sh/uv/)

A minimal terminal coding agent. The model can list, read, and write files, and run shell commands (with approval), then summarize what it did — a small, readable implementation of the LLM → tool → LLM loop using the OpenAI Responses API through OpenRouter, with a live Rich dashboard for each turn.

---

### Key Features

* Agent runtime split across `main.py`, `agent.py`, `config.py`, `schemas.py`, and `tools.py` (CLI, loop, settings, tool schemas, tool implementations).
* Four computer-facing tools — `list_files`, `read_file`, `write_file`, `run_command` — registered through a simple `tool_registry`.
* OpenRouter-backed OpenAI client (`config.py`) using the Responses API and multi-step tool calling, with a max-step guard.
* Live run dashboard in `observability.py` (Rich) that summarizes LLM steps and tool events instead of dumping raw SDK objects.
* Optional local variant in `local.py` (Pydantic AI + Ollama) for offline experiments.

---

### Architecture

```
main.py
   │
   │ user_input
   ▼
run_agent(agent_state, user_input)
   │
   ├── client.responses.create()
   │
   ├── inspect response
   │
   ├── run_tool(tool_call)
   │       │
   │       └── tool_registry → tools.py
   │
   ├── append function_call_output
   │
   ├── client.responses.create()
   │
   └── final response
```

---

### Setup and Installation (PowerShell)

1. Clone the repository:

```powershell
git clone https://github.com/JingjingYaoJerry/Mini-Agent.git
cd Mini-Agent
```

2. Install [uv](https://docs.astral.sh/uv/) if you do not already have it, then sync dependencies from `pyproject.toml` / `uv.lock`:

```powershell
uv sync
```

3. Create a `.env` file at the repository root from the example and add your OpenRouter API key:

```powershell
Copy-Item .env.example .env
```

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

Get a key at https://openrouter.ai/keys . Without this variable, the agent exits with a clear error instead of calling the API.

---

### Run the agent (CLI)

From the repository root:

```powershell
uv run python main.py
```

Or use the console script (same entry point):

```powershell
uv run mini-agent
```

Interaction:

- Type a task and press Enter → the agent may call tools, show a live dashboard for the turn, then print the final reply.
- Type `exit`, `quit`, or `q` (or press Ctrl+C) → leave the conversation.
- When the model requests `run_command`, you are prompted to approve (`y`/`n`) before anything runs.

---

### Sample prompts

Try these from the repo root after the agent starts:

1. `List the Python files in this folder and briefly say what each one is for.`
2. `Read README.md and summarize the architecture in three bullet points.`
3. `Create a file called hello_demo.txt with the text "hello from Mini-Agent", then read it back to confirm.`

(For prompt 3, the agent should ask before writing; `run_command` always asks for approval.)

---

### Project structure

```
Mini-Agent/
├── main.py                 # CLI entry point
├── agent.py                # Conversation state and LLM ↔ tool loop
├── config.py               # Model, system prompt, OpenRouter client
├── schemas.py              # Tool schemas sent to the model
├── tools.py                # Tool implementations + registry
├── observability.py        # Rich live dashboard for one turn
├── local.py                # Optional Pydantic AI + Ollama variant
├── Earlier_Stages/         # Earlier single-file experiments (see below)
├── .env.example            # Env var template (copy to .env)
├── pyproject.toml
├── uv.lock
└── README.md
```

---

### Earlier stages

`Earlier_Stages/` keeps the short scripts this project grew from — one-shot chat, multi-round memory, tool calling, then a monolithic agent — before the current module split. They are learning notes, not the supported entry point; start from `main.py` unless you are tracing how the design evolved.

---

### Acknowledgements

This project uses the [OpenAI Python SDK](https://github.com/openai/openai-python) (Responses API) via [OpenRouter](https://openrouter.ai/), [Rich](https://github.com/Textualize/rich) for the live dashboard, and [uv](https://docs.astral.sh/uv/) for dependency management. The optional `local.py` path uses [Pydantic AI](https://ai.pydantic.dev/) with a local [Ollama](https://ollama.com/) model.
