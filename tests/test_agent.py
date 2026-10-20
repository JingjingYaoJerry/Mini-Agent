import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

from rich.console import Console

import observability


# `agent.py` reads these values from config.py when it is imported.
# Avoid loading .env, constructing an API client, or reading real credentials.
offline_config = ModuleType("config")
offline_config.MODEL = "offline-test-model"
offline_config.MAX_AGENT_STEPS = 10
offline_config.SYSTEM_PROMPT = "Offline test prompt"
offline_config.client = None
with patch.dict(sys.modules, {"config": offline_config}):
    import agent
    import main


def model_response(text="", tool_calls=()):
    # A small stand-in for the parts of a Responses API reply used by the loop.
    return SimpleNamespace(
        output=list(tool_calls) or [SimpleNamespace(type="message")],
        output_text=text,
    )


def tool_call(name="read_file", arguments='{"path": "sample.txt"}', call_id="call-1"):
    # The agent routes calls by name and uses call_id to attach each result.
    return SimpleNamespace(
        type="function_call",
        name=name,
        arguments=arguments,
        call_id=call_id,
    )


class AgentTests(unittest.TestCase):
    def setUp(self):
        # Keep dashboard output in memory so tests do not need a real terminal.
        self.terminal = StringIO()
        self.create_response = Mock()
        self.read_file = Mock(return_value="sample content")
        self.enterContext(
            patch.object(
                observability,
                "console",
                Console(file=self.terminal, width=120, color_system=None),
            )
        )
        self.enterContext(
            patch.object(
                agent,
                "client",
                SimpleNamespace(
                    responses=SimpleNamespace(create=self.create_response)
                ),
            )
        )
        self.enterContext(patch.object(agent, "MAX_AGENT_STEPS", 10))
        self.enterContext(
            patch.dict(agent.tool_registry, {"read_file": self.read_file}, clear=True)
        )

    def test_turn_without_tools_completes_with_real_dashboard(self):
        response = model_response("Hello")
        self.create_response.return_value = response
        state = agent.create_agent_state()

        self.assertIs(agent.run_agent(state, "Say hello"), response)

        # A normal answer should finish without calling any tools.
        self.assertEqual(state["step"], 1)
        self.assertEqual(state["responses"], [response])
        self.assertEqual(
            state["input_items"][:2],
            [
                {"role": "developer", "content": "Offline test prompt"},
                {"role": "user", "content": "Say hello"},
            ],
        )
        self.create_response.assert_called_once()
        self.assertEqual(
            self.create_response.call_args.kwargs["model"], "offline-test-model"
        )
        self.assertIs(self.create_response.call_args.kwargs["tools"], agent.TOOLS)
        self.read_file.assert_not_called()
        self.assertIn("Completed", self.terminal.getvalue())
        self.assertIn("Hello", self.terminal.getvalue())

    def test_tool_result_is_sent_to_the_next_model_request(self):
        first = model_response(tool_calls=[tool_call()])
        final = model_response("Summary")
        responses = iter([first, final])
        request_inputs = []

        def create_response(**kwargs):
            request_inputs.append(list(kwargs["input"]))
            return next(responses)

        self.create_response.side_effect = create_response
        state = agent.create_agent_state()

        self.assertIs(agent.run_agent(state, "Read sample.txt"), final)

        # The fake file result should appear in the model's next input.
        tool_output = {
            "type": "function_call_output",
            "call_id": "call-1",
            "output": "sample content",
        }
        self.read_file.assert_called_once_with(path="sample.txt")
        self.assertEqual(self.create_response.call_count, 2)
        self.assertNotIn(tool_output, request_inputs[0])
        self.assertIn(tool_output, request_inputs[1])
        self.assertEqual(state["responses"], [first, final])
        self.assertEqual(state["step"], 2)
        self.assertIn("Completed", self.terminal.getvalue())
        self.assertIn("tools 1", self.terminal.getvalue())

    def test_step_limit_returns_pending_response_without_executing_its_tool(self):
        first = model_response(tool_calls=[tool_call()])
        pending = model_response(tool_calls=[tool_call(call_id="call-2")])
        self.create_response.side_effect = [first, pending]
        state = agent.create_agent_state()

        with patch.object(agent, "MAX_AGENT_STEPS", 2):
            self.assertIs(agent.run_agent(state, "Read again"), pending)

        # The final requested tool is left alone once the request limit is hit.
        self.assertEqual(self.create_response.call_count, 2)
        self.read_file.assert_called_once_with(path="sample.txt")
        self.assertEqual(state["step"], 2)
        self.assertEqual(pending.output_text, "")
        self.assertFalse(
            any(
                isinstance(item, dict) and item.get("call_id") == "call-2"
                for item in state["input_items"]
            )
        )
        self.assertIn("Stopped at max steps (2)", self.terminal.getvalue())

    def test_model_exception_is_displayed_and_reraised(self):
        error = RuntimeError("offline model failure")
        self.create_response.side_effect = error
        state = agent.create_agent_state()

        with self.assertRaises(RuntimeError) as caught:
            agent.run_agent(state, "Trigger a model error")

        # The dashboard shows the error, and the original exception still escapes.
        self.assertIs(caught.exception, error)
        self.assertEqual(state["responses"], [])
        self.assertEqual(state["step"], 0)
        self.read_file.assert_not_called()
        self.assertIn("Error", self.terminal.getvalue())
        self.assertIn("offline model failure", self.terminal.getvalue())

    def test_tool_exception_becomes_a_result_and_the_loop_continues(self):
        self.read_file.side_effect = OSError("offline read failure")
        final = model_response("The read failed")
        self.create_response.side_effect = [
            model_response(tool_calls=[tool_call()]),
            final,
        ]
        state = agent.create_agent_state()

        self.assertIs(agent.run_agent(state, "Read sample.txt"), final)

        # Tool errors become text results, so the model gets a chance to respond.
        self.assertIn(
            {
                "type": "function_call_output",
                "call_id": "call-1",
                "output": "Error executing tool 'read_file': offline read failure",
            },
            state["input_items"],
        )
        self.assertEqual(self.create_response.call_count, 2)
        self.assertIn("Completed", self.terminal.getvalue())

    def test_invalid_tool_calls_return_errors_without_running_tools(self):
        for call in (
            tool_call(arguments="{not json"),
            tool_call(name="unknown_tool", arguments="{}"),
        ):
            with self.subTest(name=call.name, arguments=call.arguments):
                arguments, result = agent.run_tool(call)

                self.assertEqual(arguments, {})
                self.assertTrue(result.startswith(f"Error executing tool '{call.name}':"))
        self.read_file.assert_not_called()
        self.create_response.assert_not_called()

    def test_conversation_is_retained_and_steps_reset_between_turns(self):
        first = model_response("First answer")
        second = model_response("Second answer")
        self.create_response.side_effect = [first, second]
        state = agent.create_agent_state()

        agent.run_agent(state, "First question")
        agent.run_agent(state, "Second question")

        # Messages carry over to the next turn, but the step count starts over.
        self.assertEqual(state["step"], 1)
        self.assertEqual(state["responses"], [first, second])
        self.assertEqual(
            [
                item["content"]
                for item in state["input_items"]
                if isinstance(item, dict) and item.get("role") == "user"
            ],
            ["First question", "Second question"],
        )

    def test_root_cli_prints_the_answer_and_exits(self):
        self.create_response.return_value = model_response("Offline answer")
        output = StringIO()

        with patch("builtins.input", side_effect=["", "Say hello", "q"]):
            with redirect_stdout(output):
                main.main()

        # The CLI skips blank input, handles a message, then exits on "q".
        self.create_response.assert_called_once()
        self.assertIn("LLM: Offline answer", output.getvalue())
        self.assertIn("Exiting the conversation...", output.getvalue())


if __name__ == "__main__":
    unittest.main()
