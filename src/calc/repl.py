from __future__ import annotations

import shlex
import sys
from typing import Callable

from .options import CLIOptions


def handle_repl_command(
    expr: str,
    *,
    help_text: str,
    help_chain_text: str,
    help_power_text: str,
    help_demo_text: str,
    examples_text: str,
    tutorial_text: str,
    ode_text: str,
    linalg_text: str,
    cli_name: str,
    version: str,
    print_update_status: Callable[[], None],
    style_fn: Callable[..., str],
    color_mode: str = "auto",
    stderr=sys.stderr,
) -> bool:
    if expr in {":q", ":quit", ":x"}:
        raise EOFError
    if expr in {":h", ":help"}:
        print(help_text)
        return True
    if expr == "?":
        print(help_text)
        print(help_chain_text)
        return True
    if expr == "??":
        print(help_power_text)
        return True
    if expr == "???":
        print(help_demo_text)
        return True
    if expr == ":examples":
        print(examples_text)
        return True
    if expr in {":tutorial", ":tour"}:
        print(tutorial_text)
        return True
    if expr == ":ode":
        print(ode_text)
        return True
    if expr in {":linalg", ":la"}:
        print(linalg_text)
        return True
    if expr in {":v", ":version"}:
        print(f"{cli_name} v{version}")
        return True
    if expr in {":update", ":check"}:
        print_update_status()
        return True
    if expr.startswith(":"):
        print(style_fn("E: unknown command", color="red", stream=stderr, color_mode=color_mode), file=stderr)
        print(
            style_fn("hint: use :h to list commands", color="yellow", stream=stderr, color_mode=color_mode),
            file=stderr,
        )
        return True
    return False


def tutorial_command(
    expr: str,
    state: dict | None,
    *,
    tutorial_steps: tuple[str, ...],
    print_tutorial_step: Callable[[int], None],
    stderr=sys.stderr,
) -> bool:
    if state is None:
        return False
    if expr in {":tutorial", ":tour"}:
        state["active"] = True
        state["index"] = 0
        print("tutorial mode started. use :next, :repeat, :done")
        print_tutorial_step(state["index"])
        return True
    if expr == ":next":
        if not state.get("active", False):
            print("hint: start with :tutorial", file=stderr)
            return True
        nxt = state["index"] + 1
        if nxt >= len(tutorial_steps):
            print("tutorial complete. use :done to exit tutorial mode")
            return True
        state["index"] = nxt
        print_tutorial_step(state["index"])
        return True
    if expr == ":repeat":
        if not state.get("active", False):
            print("hint: start with :tutorial", file=stderr)
            return True
        print_tutorial_step(state["index"])
        return True
    if expr == ":done":
        if state.get("active", False):
            state["active"] = False
            print("tutorial mode ended")
        else:
            print("hint: tutorial is not active; use :tutorial", file=stderr)
        return True
    return False


def try_parse_repl_inline_options(
    expr: str,
    *,
    cli_name: str,
    parse_options_fn: Callable[[list[str]], CLIOptions],
) -> CLIOptions | None:
    line = expr.strip()
    if line.startswith(f"{cli_name} "):
        line = line[len(cli_name) :].strip()
    elif not line.startswith("-"):
        return None
    try:
        tokens = shlex.split(line)
    except ValueError as exc:
        raise ValueError(f"invalid REPL option input: {exc}") from exc
    return parse_options_fn(tokens)
