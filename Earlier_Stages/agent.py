

import json
import os
import subprocess

from dotenv import load_dotenv
from earlier_stages.observability import print_response
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

# The four tools -- list_files, read_file, write_file, run_command, are close to a 
# minimal physical interface to a computer; with an LLM that has sufficient reasoning 
# and coding capabilities, they give the LLM the ability to perform: 
# observe → understand → modify → execute → observe again
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
    """Write content to a file at the specified path."""
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)
    return f"Saved {path} ({len(content)} characters)."

def run_command(command):
    """Run a shell command and return its output where the user approves it first."""
    result = input(f"Run command '{command}'? (y/n): ")
    if result.strip().lower() != "y":
        return "The user has declined to run the command."
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
    return (result.stdout + result.stderr).strip() or f"(no output, exit code {result.returncode})"


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Define the tool schema for Responses API (following the pattern of OpenAI's tool calling example)
tools = [
    {
        "type": "function", 
        "name": "list_files", 
        "description": "List files in a directory. Folders end with a forward slash.", 
        "parameters": {
            "type": "object", 
            "properties": {
                "path": {
                    "type": "string", 
                    "description": "The path to the directory to list files in, e.g., '.'", 
                }
            },
            "required": ["path"], 
            "additionalProperties": False,  # needed under the default strict mode
        }, 
    },
    {
        "type": "function", 
        "name": "read_file", 
        "description": "Read a text file and return its content", 
        "parameters": {
            "type": "object", 
            "properties": {
                "path": {
                    "type": "string", 
                    "description": "The path to the text file to read", 
                }
            },
            "required": ["path"], 
            "additionalProperties": False,  # needed under the default strict mode
        }, 
    }, 
    {
        "type": "function", 
        "name": "write_file", 
        "description": "Write content to a text file", 
        "parameters": {
            "type": "object", 
            "properties": {
                "path": {
                    "type": "string", 
                    "description": "The path to the text file to write to", 
                }, 
                "content": {
                    "type": "string", 
                    "description": "The content to write to the file", 
                }
            },
            "required": ["path", "content"], 
            "additionalProperties": False,  # needed under the default strict mode
        }, 
    }, 
    {
        "type": "function", 
        "name": "run_command", 
        "description": "Run a shell command and return its output where the user approves it first", 
        "parameters": {
            "type": "object", 
            "properties": {
                "command": {
                   "type": "string", 
                    "description": "The shell command to run", 
                }
            },
            "required": ["command"], 
            "additionalProperties": False,  # needed under the default strict mode
        }, 
    }, 
]

tool_registry = {
    "list_files": list_files, 
    "read_file": read_file, 
    "write_file": write_file, 
    "run_command": run_command, 
}  # for dynamic routing, decoupling and centralized management of tools


# Use the model's own session-wise response chain to maintain the conversation context
# messages = []
# previous_response_id = None
# Not really working possibly because of OpenRouter's configurations -- use agent_state to maintain the conversation context instead
agent_state = {
    "input_items": [
        {
            "role": "developer", 
            "content": SYSTEM_PROMPT, 
        }
    ],  # likely 'developer' -> 'user #1' -> 'reasoning' -> 'tool_call' -> 'tool_output' -> 'message' -> 'user #2'
    "responses": [], 
    "step": 0,  # for both tracking and preventing infinite loops
}

while True:
    user_input = input("User: ")  # get user input

    # The exit
    if user_input.strip().lower() in ("exit", "quit", "q"):
        print("Exiting the conversation...")
        break

    # Include the system prompt in every request to apply strict behavioral control
    agent_state["input_items"].append(
        {
            "role": "user", 
            "content": user_input, 
        }
    )
    agent_state["step"] = 0

    response = client.responses.create(  # Responses API instead of Chat Completions API
        model=MODEL,
        tools=tools,  # include the tool schema also in the request
        input=agent_state["input_items"], 
        # previous_response_id=previous_response_id,  # if the model does keep the so-called session-wise response chain, i.e., the conversation context
        # messages=[
        #     {
        #         "role": "system",
        #         "content": SYSTEM_PROMPT
        #     },  # the specification that should be understood by the model since the beginning
            
        #     *messages,  # unpack and include all previous messages in the conversation
        # ]
    )
    # messages.append({"role": "assistant", "content": response.output_text})
    agent_state["input_items"].extend(response.output)  # separately append the json-structured output items to the conversation context (e.g., reasoning, function_call)
    agent_state["responses"].append(response)  # append the model's response to the conversation context
    agent_state["step"] += 1
    
    # For debugging
    print_response(response)  # print the model's response in a structured way

    # ---------------------------------------------------------
    # Agent loop of tool callings (if any)
    # ---------------------------------------------------------
    while True:  # loop until the model finishes the (chain of) of tool calls

        # List function calls produced by the model
        function_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        # No function call → final answer
        if not function_calls:
            break

        if agent_state["step"] >= MAX_AGENT_STEPS:
            print(f"Agent stopped after reaching the maximum number of steps: {MAX_AGENT_STEPS}.")
            break

        for tool_call in function_calls:

            tool_name = tool_call.name

            # ---------------------------------------------------------
            # The actual tool calling and execution (dynamic routing)
            # ---------------------------------------------------------
            try:
                args = json.loads(tool_call.arguments)

                print(
                    f"Be aware! The model is requesting "
                    f"to call '{tool_name}' with arguments: {args}"
                )

                tool_function = tool_registry.get(tool_name)  # the dynamic routing

                if tool_function is None:
                    raise ValueError(f"Unknown tool called: {tool_name}")

                result = tool_function(**args)

                print(
                    f"Tool '{tool_name}' executed successfully.\n"
                    f"Result:\n{result}"
                )

            except Exception as e:
                result = f"Error executing tool '{tool_name}': {e}"  # to be returned to the model for further reasoning
                print(result)

            agent_state["input_items"].append(
                {
                    "type": "function_call_output", 
                    "call_id": tool_call.call_id, 
                    "output": str(result), 
                }
            )  # append the tool outputs to the conversation context as it's one single item (round)

        # Give the tool results back to the model
        response = client.responses.create(
            model=MODEL, 
            tools=tools, 
            input=agent_state["input_items"], 
            # previous_response_id=response.id, 
        )
        agent_state["input_items"].extend(response.output)  # separately append the json-structured output items to the conversation context (e.g., reasoning, function_call)
        agent_state["responses"].append(response)
        agent_state["step"] += 1

        # For debugging
        print_response(response)  # print the model's response in a structured way

    # ---------------------------------------------------------
    # Final answer (or simply the raw-text message if no tool is called)
    # ---------------------------------------------------------
    print(f"LLM: {response.output_text}")
    # messages.append({"role": "assistant", "content": response})
    # previous_response_id = response.id



# 一个更工程化的结构可以是：
# project/
# │
# ├── main.py
# │
# ├── agent.py
# │   │
# │   ├── AgentState
# │   ├── run_agent()
# │   ├── execute_tool()
# │   └── agent loop
# │
# ├── tools.py
# │   └── read_file()
# │
# ├── observability.py
# │   └── Agent tracing / Rich
# │
# └── config.py
#     ├── MODEL
#     ├── client
#     └── system prompt

# main.py
#     ↓
# 负责 CLI / user interaction

# agent.py
#     ↓
# 负责
# LLM → tool → LLM → tool → final

# tools.py
#     ↓
# 负责真正执行工具

# observability.py
#     ↓
# 负责
# "这次 Agent 到底干了什么？"

# config.py
#     ↓
# 负责
# "我现在使用哪个 model / gateway？"