from time import perf_counter

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


console = Console()


class AgentDashboard:
    """Compact Live view of one agent run.

    The dashboard summarizes the run instead of dumping raw SDK objects.
    Raw Responses API objects remain available in agent_state["responses"].
    """

    def __init__(self, max_events=12):
        self.max_events = max_events
        self.events = []
        self.step = 0
        self.tool_count = 0
        self.start_time = perf_counter()
        self.status = "Running"
        self.user_prompt = ""

    def start(self, user_prompt):
        self.user_prompt = user_prompt
        self.start_time = perf_counter()
        self.status = "Running"
        self.events.clear()
        self.step = 0
        self.tool_count = 0

    def add_llm(self, response, step):
        self.step = step
        output_types = [getattr(item, "type", "?") for item in response.output]
        summary = ", ".join(output_types) if output_types else "no output items"
        self._add_event("LLM", f"step {step}  •  {summary}")

    def add_tool(self, tool_name, args, result, step):
        self.step = step
        self.tool_count += 1
        self._add_event(
            "TOOL",
            f"step {step}  •  {tool_name}\n"
            f"args: {self._format(args, 160)}\n"
            f"result: {self._format(result, 220)}",
        )

    def finish(self, response=None, status="Completed"):
        self.status = status
        if response is not None:
            self._add_event("FINAL", self._format(response.output_text, 300))

    def error(self, message):
        self.status = "Error"
        self._add_event("ERROR", str(message))

    def _add_event(self, kind, body):
        self.events.append((kind, body))
        self.events = self.events[-self.max_events:]

    @staticmethod
    def _format(value, limit):
        text = str(value).replace("\n", " ")
        return text if len(text) <= limit else text[:limit - 3] + "..."

    def render(self):
        elapsed = perf_counter() - self.start_time

        header = Table.grid(expand=True)
        header.add_column()
        header.add_column(justify="right")
        header.add_row(Text("Coding Agent", style="bold"), Text(self.status))
        header.add_row(
            Text(f"Task: {self._format(self.user_prompt, 100)}"),
            Text(f"{elapsed:.1f}s  •  steps {self.step}  •  tools {self.tool_count}"),
        )

        timeline = Table.grid(padding=(0, 1))
        timeline.add_column(width=4, justify="right")
        timeline.add_column(width=7)
        timeline.add_column()

        for index, (kind, body) in enumerate(self.events, start=1):
            marker = {"LLM": "LLM", "TOOL": "TOOL", "FINAL": "DONE", "ERROR": "ERR"}.get(
                kind, kind
            )
            timeline.add_row(str(index), marker, body)

        return Panel(
            Group(header, Text(""), timeline),
            title="Agent Run",
            border_style="cyan",
            padding=(1, 2),
        )


class DashboardContext:
    """Keep the dashboard live while run_agent is executing."""

    def __init__(self, dashboard):
        self.dashboard = dashboard
        self.live = Live(
            dashboard.render(),
            console=console,
            refresh_per_second=8,
            transient=False,
        )

    def __enter__(self):
        self.live.start(refresh=True)
        return self.dashboard

    def __exit__(self, exc_type, exc, tb):
        self.live.update(self.dashboard.render(), refresh=True)
        self.live.stop()
        return False

    def update(self):
        self.live.update(self.dashboard.render(), refresh=True)


# Convenience method used by the exception path.
def _refresh(self):
    console.print(self.render())


AgentDashboard.refresh = _refresh
