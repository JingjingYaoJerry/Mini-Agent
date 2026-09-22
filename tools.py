# The component of an agent runtime responsible for the implementation of the tools, 
# and the dynamic routing of tool calls, i.e., the tool registry.
# The four tools -- list_files, read_file, write_file, run_command, are close to a
# minimal physical interface to a computer; with an LLM that has sufficient reasoning
# and coding capabilities, they give the LLM the ability to perform:
# observe → understand → modify → execute → observe again

import os
import subprocess


def list_files(path="."):
    """List files in the specified directory. Folders end with a forward slash."""
    entries = []
    for entry in os.scandir(path):
        entries.append(entry.name + ("/" if entry.is_dir() else ""))
    return "\n".join(sorted(entries)) or "(empty directory)"


def read_file(path):
    """Read the content of a file given its path."""
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_file(path, content):
    """Write content to a text file given its path."""
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)
    return f"Saved {path} ({len(content)} characters)."


def run_command(command):
    """Run a shell command after asking the user for approval."""
    approval = input(f"Run command '{command}'? (y/n): ")
    if approval.strip().lower() != "y":
        return "The user has declined to run the command."

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return (result.stdout + result.stderr).strip() or f"(no output, exit code {result.returncode})"


tool_registry = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
}  # for dynamic routing, decoupling and centralized management of tools
