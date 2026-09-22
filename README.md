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