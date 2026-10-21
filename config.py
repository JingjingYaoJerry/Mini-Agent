# The component of an agent runtime responsible for the configs and environment setup.
# config.py
#     ├── MODEL
#     ├── MAX_AGENT_STEPS
#     ├── SYSTEM_PROMPT
#     └── client

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # Load environment variables from .env file

MODEL = "~openai/gpt-latest"  # specify the model to use
MAX_AGENT_STEPS = 10

SYSTEM_PROMPT = """
You are a coding agent running in the user's terminal.
You can list files, read files, write files, and run shell commands.
Use your tools to complete the user's tasks, then briefly summarize what you did.
The working directory is the folder the user launched you from.
Ask before making any change; do not make any change without the user's permission.
Make sure the user's intent is fully understood before taking any action.
"""

_api_key = os.getenv("OPENROUTER_API_KEY")
if not _api_key:
    raise SystemExit(
        "Missing OPENROUTER_API_KEY. "
        "Copy .env.example to .env and set your OpenRouter API key."
    )

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=_api_key,
)