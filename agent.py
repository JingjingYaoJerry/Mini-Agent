# The main component of an agent runtime responsible for the conversation context, i.e.,
# LLM → tool → LLM → tool → final
# It keeps the conversation context and runs one complete user turn.

import json

from config import MAX_AGENT_STEPS, MODEL, SYSTEM_PROMPT, client
from observability import AgentDashboard, DashboardContext
from schemas import TOOLS
from tools import tool_registry


def create_agent_state():
    return {
        "input_items": [
            {
                "role": "developer",
                "content": SYSTEM_PROMPT,
            }
        ],
        "responses": [],
        "step": 0,  # for both tracking and preventing infinite loops
    }


def run_tool(tool_call):
    """Resolve and execute one model-requested tool."""
    tool_name = tool_call.name

    # The actual tool calling and execution (dynamic routing)
    try:
        args = json.loads(tool_call.arguments)
        tool_function = tool_registry.get(tool_name)  # the dynamic routing

        if tool_function is None:
            raise ValueError(f"Unknown tool called: {tool_name}")

        result = tool_function(**args)
        return args, result

    except Exception as exc:
        return {}, f"Error executing tool '{tool_name}': {exc}"


def _request_model(agent_state):
    response = client.responses.create(  # Responses API instead of Chat Completions API
        model=MODEL,
        tools=TOOLS,  # include the tool schema (not the implementations) in the request
        input=agent_state["input_items"],
    )
    agent_state["input_items"].extend(response.output)  # separately append the json-structured output items to the conversation context
    agent_state["responses"].append(response)  # append the model's response to the conversation context
    agent_state["step"] += 1
    return response


def run_agent(agent_state, user_input):
    """Run one user turn, including the complete tool-calling loop."""
    agent_state["input_items"].append(
        {
            "role": "user",
            "content": user_input,
        }
    )
    agent_state["step"] = 0

    dashboard = AgentDashboard()
    dashboard.start(user_input)

    try:
        dashboard_context = DashboardContext(dashboard)
        with dashboard_context:
            response = _request_model(agent_state)
            dashboard.add_llm(response, agent_state["step"])
            dashboard_context.update()

            # ---------------------------------------------------------
            # Agent loop of tool callings (if any)
            # ---------------------------------------------------------
            while True:  # loop until the model finishes the (chain) of tool calls
                function_calls = [
                    item
                    for item in response.output
                    if item.type == "function_call"
                ]

                # No function call → final answer
                if not function_calls:
                    dashboard.finish(response)
                    dashboard_context.update()
                    return response

                if agent_state["step"] >= MAX_AGENT_STEPS:
                    dashboard.finish(
                        status=f"Stopped at max steps ({MAX_AGENT_STEPS})"
                    )
                    dashboard_context.update()
                    return response

                for tool_call in function_calls:
                    args, result = run_tool(tool_call)

                    dashboard.add_tool(
                        tool_call.name,
                        args,
                        result,
                        agent_state["step"],
                    )

                    agent_state["input_items"].append(
                        {
                            "type": "function_call_output",
                            "call_id": tool_call.call_id,
                            "output": str(result),
                        }
                    )  # append the tool outputs to the conversation context as it's one single item (round)
                    dashboard_context.update()

                # Give the tool results back to the model
                response = _request_model(agent_state)
                dashboard.add_llm(response, agent_state["step"])
                dashboard_context.update()

    except Exception as exc:
        dashboard.error(exc)
        dashboard.refresh()
        raise
