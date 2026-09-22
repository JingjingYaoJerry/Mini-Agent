# Enabls newer Python features and syntax in older Python versions
from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table
from rich.pretty import Pretty


console = Console()


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """Safely read an attribute from SDK objects or dicts."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _safe_json(value: Any) -> str:
    """Serialize values for display without assuming a fixed SDK schema."""
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return repr(value)


def print_response(response: Any, *, show_raw_unknown: bool = True) -> None:
    """Pretty-print useful response information without assuming one provider schema."""
    table = Table(title="Response", show_lines=False)
    table.add_column("Attribute", style="bold")
    table.add_column("Value")

    # These are intentionally accessed defensively. Missing fields simply disappear.
    for name in (
        "id",
        "object",
        "model",
        "status",
        "created_at",
        "completed_at",
        "previous_response_id",
        "store",
        "parallel_tool_calls",
        "tool_choice",
        "truncation",
        "max_output_tokens",
        "max_tool_calls",
    ):
        value = _get(response, name)
        if value is not None:
            table.add_row(name, repr(value))

    usage = _get(response, "usage")
    if usage is not None:
        usage_table = Table(title="Usage")
        usage_table.add_column("Metric", style="bold")
        usage_table.add_column("Value")
        for name in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cost",
        ):
            value = _get(usage, name)
            if value is not None:
                usage_table.add_row(name, repr(value))
        console.print(table)
        console.print(usage_table)
    else:
        console.print(table)

    output = _get(response, "output", [])
    if output is not None:
        for index, item in enumerate(output):
            print_output_item(item, index=index, show_raw_unknown=show_raw_unknown)

    text = _get(response, "output_text")
    if text:
        console.print(Panel(text, title="Output Text"))


def print_output_item(
    item: Any,
    *,
    index: int = 0,
    show_raw_unknown: bool = True,
) -> None:
    """Display an output item using type when available, with graceful fallback."""
    item_type = _get(item, "type", "unknown")

    if item_type == "function_call":
        name = _get(item, "name")
        call_id = _get(item, "call_id")
        arguments = _get(item, "arguments")

        body = (
            f"[bold]Name:[/bold] {name}\n"
            f"[bold]Call ID:[/bold] {call_id}\n"
            f"[bold]Arguments:[/bold]\n"
        )

        if arguments:
            try:
                console.print(
                    Panel(
                        body,
                        title=f"Output #{index} — function_call",
                    )
                )
                console.print(JSON(arguments))
            except Exception:
                console.print(
                    Panel(
                        body + str(arguments),
                        title=f"Output #{index} — function_call",
                    )
                )
        else:
            console.print(
                Panel(body, title=f"Output #{index} — function_call")
            )
        return

    if item_type == "message":
        content = _get(item, "content")
        console.print(
            Panel(
                Pretty(content),
                title=f"Output #{index} — message",
            )
        )
        return

    if item_type == "reasoning":
        summary = _get(item, "summary")
        console.print(
            Panel(
                Pretty(summary),
                title=f"Output #{index} — reasoning",
            )
        )
        return

    # Future/unknown output types: don't crash just because the provider changed.
    if show_raw_unknown:
        console.print(
            Panel(
                Pretty(item),
                title=f"Output #{index} — {item_type}",
            )
        )



# Normalized Telemetry 可以定义成：
# AgentResponse
# ├── id
# ├── model
# ├── status
# ├── latency
# ├── usage
# │   ├── input_tokens
# │   ├── output_tokens
# │   └── cost
# └── output_items
#     ├── reasoning
#     ├── function_call
#     └── message