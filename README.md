# Mini-Agent

Mini-Agent is a small Python program that runs in a terminal. It sends a
message to a language model, lets the model request a tool, and sends the
tool's result back to the model.

## Run it

You need Python 3.12 or later and [uv](https://docs.astral.sh/uv/).

Install the dependencies:

```powershell
uv sync --locked
```

Create a `.env` file in the project folder with an OpenRouter API key:

```dotenv
OPENROUTER_API_KEY=your_key_here
```

Then start the program:

```powershell
uv run python main.py
```

Type `q`, `quit`, or `exit` to stop. Requests to a hosted model may cost money.

## Tools

The program has four tools:

- `list_files` shows the files in a folder.
- `read_file` reads a text file.
- `write_file` creates or replaces a text file.
- `run_command` asks before running a shell command.

The confirmation only applies to shell commands. File reads and writes do not
ask first, and paths are not limited to the project folder. The tools run on
the local computer, not in a sandbox. Use a test folder and avoid sensitive
files.

## Tests

Run the tests with `uv run python -m unittest discover -s tests -v`. They use
fake model responses and do not contact OpenRouter. A live model request has
not been verified.
