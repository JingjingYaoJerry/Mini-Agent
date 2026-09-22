# Visualizing how agent_state["input_items"] grows over multiple turns:
#
# Turn 1 (the user has only prompted once):
#
# input_items
# ├── [0] developer
# │       "You are a helpful assistant..."
# ├── [1] user
# │       "What is in test.txt?"
# ├── [2] reasoning
# │       ...
# ├── [3] function_call
# │       name="read_file"
# │       arguments={"path": "test.txt"}
# ├── [4] function_call_output
# │       output="Hi There!"
# ├── [5] reasoning
# │       ...
# └── [6] message
#         "The file contains: Hi There!"
#
# Turn 2 (the user has only prompted twice):
#
# input_items
# ├── [0] developer
# ├── [1] user
# ├── [2] reasoning
# ├── [3] function_call
# ├── [4] function_call_output
# ├── [5] reasoning
# ├── [6] message
# └── [7] user
#         "Can you explain that?"
#
# Turn 3 (the user has only prompted thrice):
#
# input_items
# ├── [0] developer
# ├── ...
# ├── [6] message
# ├── [7] user
# ├── [8] reasoning
# ├── [9] message
# └── [10] user
#          "Now summarize it."

import json
import os

from dotenv import load_dotenv
from earlier_stages.observability import print_response
from openai import OpenAI

load_dotenv()  # Load environment variables from .env file


MODEL = "~openai/gpt-latest"  # specify the model to use
MAX_AGENT_STEPS = 10
SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "Answer accurately and concisely."
)


def read_file(path):
    """Read the content of a file given its path."""
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Define the tool schema for Responses API (following the pattern of OpenAI's tool calling example)
tools = [
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
]

tool_registry = {
    "read_file": read_file, 
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