# The component of an agent runtime responsible for describing the tools to the model.
# It is kept separate from the tool-execution and tool-registry implementation in tools.py 
# for decoupling, and centralized management.

TOOLS = [
    {
        "type": "function",
        "name": "list_files",
        "description": "List files in a directory. Folders end with a forward slash.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the directory to list files in, e.g., '.'.",
                }
            },
            "required": ["path"],
            "additionalProperties": False,  # needed under the default strict mode
        },
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read a text file and return its content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the text file to read.",
                }
            },
            "required": ["path"],
            "additionalProperties": False,  # needed under the default strict mode
        },
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Write content to a text file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the text file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            "required": ["path", "content"],
            "additionalProperties": False,  # needed under the default strict mode
        },
    },
    {
        "type": "function",
        "name": "run_command",
        "description": "Run a shell command and return its output after user approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run.",
                }
            },
            "required": ["command"],
            "additionalProperties": False,  # needed under the default strict mode
        },
    },
]
