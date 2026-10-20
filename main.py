# The CLI entry point for the coding agent.
# It creates one agent state for the conversation, reads user input,
# and delegates the actual LLM → tool → LLM loop to agent.py.

from agent import create_agent_state, run_agent


def main():
    # Keep one conversation state so the agent can remember earlier turns.
    agent_state = create_agent_state()

    while True:
        try:
            user_input = input("User: ")  # get user input
        except (EOFError, KeyboardInterrupt):
            print("\nExiting the conversation...")
            break

        # The exit
        if user_input.strip().lower() in ("exit", "quit", "q"):
            print("Exiting the conversation...")
            break

        if not user_input.strip():
            continue

        # agent.py handles the model/tool loop and gives back the final reply.
        response = run_agent(agent_state, user_input)
        print(f"\nLLM: {response.output_text}\n")


if __name__ == "__main__":
    main()
