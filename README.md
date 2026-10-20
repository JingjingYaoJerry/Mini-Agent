# Mini-Agent

This is a small project I made to learn how an AI agent can use tools. It runs
in a terminal and can ask a language model to list files, read or write a file,
or run a command. This is a learning project, not a finished or production-ready
agent.

## How it works

I split the main parts into a few Python files:

- `main.py` asks me for a message and prints the final answer.
- `agent.py` sends the conversation to the model and handles tool requests.
- `schemas.py` describes the tools the model is allowed to request.
- `tools.py` contains the Python functions that do the actual work.
- `config.py` contains the model settings and OpenRouter connection.
- `observability.py` shows a small Rich dashboard while a turn is running.

The basic loop is:

```text
My message -> model reply -> maybe run a tool -> send the result back -> answer
```

The conversation is kept in memory while the program is running. It is not
saved after the program closes. Each turn can make up to 10 model requests;
reaching that limit can stop the turn before it gets a final answer.

## Tools and safety

There are four tools: `list_files` lists one folder, `read_file` reads a UTF-8
file, `write_file` creates or replaces a UTF-8 file, and `run_command` asks
before running a shell command.

Only shell commands have a confirmation prompt. File reads and writes do not,
and file paths are not restricted to the project folder. A confirmed command
still runs on my computer; the prompt is not a sandbox. For that reason, use a
test folder and do not keep sensitive files there.

## Try the project

You need Python 3.12 or newer and [uv](https://docs.astral.sh/uv/). From the
project folder, install the locked dependencies:

```powershell
uv sync --locked
```

Create a `.env` file in the project folder and add your own OpenRouter API key:

```dotenv
OPENROUTER_API_KEY=your_key_here
```

The `.env` file is ignored by Git. The model name is set in `config.py`; it is
not read from `.env`. Check that the model is available to your account before
trying it. A real request may cost money.

Start the program from the project folder:

```powershell
uv run python main.py
```

At the `User:` prompt, enter a message. Type `q`, `quit`, or `exit` to leave.

## Tests

Run the offline tests with:

```powershell
uv run python -m unittest discover -s tests -v
```

The tests use a fake model response, so they do not call OpenRouter or run real
file or shell commands. They help me check the conversation loop, tool results,
and error handling, but they do not tell me whether a real model will work.
I have not verified this project with a live model request.
