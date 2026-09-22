"""A small, self-contained agent that runs against a local Ollama model.

The Pydantic-AI agent handles the model -> tool -> model cycle.  This file
keeps the CLI, tool implementations, model configuration, and conversation
history together so it can be run directly with ``python local.py``.
"""

import os
from datetime import datetime

from pydantic_ai import Agent
from pydantic_ai.exceptions import AgentRunError, ModelAPIError
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider


# Hide the pydantic-ai startup banner in this small CLI.
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

REQUEST_TIMEOUT_SECONDS = 1800


# Ollama must be running locally and must have this model available.
MODEL = OllamaModel(
    model_name="gemma4:26b",
    provider=OllamaProvider(base_url="http://localhost:11434/v1"),
    settings={"timeout": REQUEST_TIMEOUT_SECONDS},
)


def get_current_time() -> str:
    """Return the current local date and time."""
    return datetime.now().astimezone().strftime("%A, %B %d, %Y at %I:%M %p %Z")


def calculate(expression: str) -> str:
    """Evaluate basic arithmetic without allowing names or function calls."""
    if not expression.strip():
        return "Error: the expression is empty."

    if not set(expression).issubset("0123456789+-*/(). "):
        return "Error: only numbers and basic arithmetic operators are allowed."

    try:
        # The character check above prevents names, but disabling builtins also
        # makes the evaluation boundary explicit.
        return str(eval(expression, {"__builtins__": {}}, {}))
    except (ArithmeticError, SyntaxError, TypeError, ValueError) as exc:
        return f"Error: {exc}"


def read_file(path: str) -> str:
    """Read and return a UTF-8 text file."""
    if not os.path.isfile(path):
        return f"Error: file not found: {path}"

    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except OSError as exc:
        return f"Error reading '{path}': {exc}"


def write_file(path: str, content: str) -> str:
    """Create or overwrite a UTF-8 text file and return a save confirmation."""
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return f"Saved {path} ({len(content)} characters)."
    except OSError as exc:
        return f"Error writing '{path}': {exc}"


def print_streamed_response(result) -> None:
    """Print thinking parts and final text as they stream in."""
    printed_lengths = {}
    current_section = None

    print()
    for response in result.stream_response(debounce_by=None):
        for index, part in enumerate(response.parts):
            part_kind = getattr(part, "part_kind", None)
            if part_kind not in ("thinking", "text"):
                continue

            content = getattr(part, "content", "")
            printed_key = (index, part_kind)
            printed_length = printed_lengths.get(printed_key, 0)
            if len(content) <= printed_length:
                continue

            if part_kind != current_section:
                label = "Thinking" if part_kind == "thinking" else "LLM"
                prefix = "" if current_section is None else "\n"
                print(f"{prefix}{label}: ", end="", flush=True)
                current_section = part_kind

            print(content[printed_length:], end="", flush=True)
            printed_lengths[printed_key] = len(content)
    print("\n")


# Pydantic-AI converts these Python functions into tool schemas and executes
# them whenever the Ollama model decides that a tool is needed.
agent = Agent(
    model=MODEL,
    tools=[get_current_time, calculate, read_file, write_file],
    instructions=(
        "You are a helpful assistant running 100% locally on a Ollama model. "
        "Use the available tools whenever they are useful. "
        "For file requests, ask for a path only when the user has not provided one. "
    ),
)


def main() -> None:
    """Run the interactive multi-turn agent conversation."""
    print("Starting the interactive conversation with the local Ollama model...")
    print("Local Ollama model is ready. Type 'exit', 'quit', or 'q' to end the conversation.")
    message_history = None

    while True:
        try:
            user_input = input("User: ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting the conversation...")
            break

        if user_input.strip().lower() in ("exit", "quit", "q"):
            print("Exiting the conversation...")
            break

        if not user_input.strip():
            continue

        try:
            with agent.run_stream_sync(  # Output in real-time as the model generates it
                user_input,
                message_history=message_history,
            ) as result:
                print_streamed_response(result)

            # Preserve the complete conversation, including tool calls and
            # tool results, for the next turn.
            message_history = result.all_messages()
        except (AgentRunError, ModelAPIError, OSError, ValueError) as exc:
            print(f"\nAgent error ({type(exc).__name__}): {exc}\n")


if __name__ == "__main__":
    main()