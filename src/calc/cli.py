from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from json import JSONDecodeError, dumps, loads
from importlib.metadata import PackageNotFoundError, version as package_version
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import urlopen

from sympy import Eq, dsolve
from sympy import latex as to_latex
from sympy.core.function import AppliedUndef

from .core import evaluate, normalize_expression
from .diagnostics import (
    eq_has_top_level_comma as _eq_has_top_level_comma,
    hint_for_error as _hint_for_error,
    parse_explanation,
    relaxed_rewrite_messages,
    should_print_wolfram_hint,
)

PACKAGE_NAME = "philcalc"
CLI_NAME = "phil"
UPDATE_CMD = "uv tool upgrade philcalc"
FORMAT_MODES = ("plain", "pretty", "latex", "latex-inline", "latex-block", "json")


@dataclass(frozen=True)
class CLIOptions:
    format_mode: str = "plain"
    relaxed: bool = True
    simplify_output: bool = True
    explain_parse: bool = False
    always_wa: bool = False
    copy_wa: bool = False
    color_mode: str = "auto"
    remaining: tuple[str, ...] = ()


def _calc_version() -> str:
    try:
        return package_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "dev"


VERSION = _calc_version()
PROMPT = f"{CLI_NAME}> "
HELP_TEXT = (
    f"{CLI_NAME} v{VERSION} - symbolic CLI calculator\n"
    "\n"
    "usage:\n"
    f"  {CLI_NAME} [--format MODE] [--latex|--latex-inline|--latex-block] [--strict] [--no-simplify] [--explain-parse] [--wa] [--copy-wa] [--color MODE] '<expression>'\n"
    f"  {CLI_NAME}\n"
    f"  {CLI_NAME} :examples\n"
    "\n"
    "options:\n"
    "  --format MODE   output mode: plain, pretty, latex, latex-inline, latex-block, json\n"
    "  --latex         print raw LaTeX (no delimiters)\n"
    "  --latex-inline  print LaTeX wrapped as $...$\n"
    "  --latex-block   print LaTeX wrapped as $$...$$\n"
    "  --strict        disable relaxed input parsing\n"
    "  --no-simplify   skip simplify() on parsed expressions\n"
    "  --explain-parse show normalized expression on stderr\n"
    "  --wa            always print WolframAlpha equivalent link\n"
    "  --copy-wa       copy WolframAlpha link to clipboard when shown\n"
    "  --color MODE    diagnostics color: auto, always, never\n"
    "\n"
    "upgrade:\n"
    f"  {UPDATE_CMD}\n"
    "\n"
    "repl commands:\n"
    "  :h, :help      show this help\n"
    "  :examples      show example expressions\n"
    "  :tutorial      show guided tour for new users\n"
    "  :ode           show ODE quick reference and templates\n"
    "  :next          next tutorial step (after :tutorial)\n"
    "  :repeat        repeat current tutorial step\n"
    "  :done          exit tutorial mode\n"
    "  :v, :version   show version\n"
    "  :update, :check  check current vs latest version\n"
    "  :q, :quit, :x  quit\n"
    "\n"
    "quick examples:\n"
    "  (1 - 25e^5)e^{-5t} + (25e^5 - 1)t e^{-5t} + t e^{-5t} ln(t)\n"
    "  d(x^3 + 2*x, x)\n"
    "  int(sin(x), x)\n"
    "  solve(x^2 - 4, x)\n"
    "  N(pi, 20)"
)
EXAMPLES_TEXT = (
    "examples:\n"
    "  1/3 + 1/6\n"
    "  d(x^3 + 2*x, x)\n"
    "  int(sin(x), x)\n"
    "  solve(x^2 - 4, x)\n"
    "  (854/2197)e^{8t}+(1343/2197)e^{-5t}+((9/26)t^2 -(9/169)t)e^{8t}\n"
    "  dsolve(Eq(f(t).diff(t), f(t)), f(t))\n"
    "  N(pi, 20)"
)
TUTORIAL_TEXT = (
    "guided tour:\n"
    "  1) Start: phil '2+2'\n"
    "  2) Core ops: phil 'd(x^3 + 2*x, x)' / phil 'int(sin(x), x)' / phil 'solve(x^2 - 4, x)'\n"
    "  3) REPL: phil, then try d(x^2, x), A=Matrix([[1,2],[3,4]]), det(A), ans+1\n"
    "  4) ODE input: dy/dx = y ; y' = y ; \\frac{dy}{dx} = y\n"
    "  5) Solve ODE: dsolve(Eq(d(y(x), x), y(x)), y(x))\n"
    "  6) LaTeX style: $d(x^2, x)$ ; \\sin(x)^2 + \\cos(x)^2\n"
    "  7) Use :examples for more patterns\n"
    "full tutorial: TUTORIAL.md"
)
ODE_TEXT = (
    "ode quick reference:\n"
    "  quick start (human style):\n"
    "    ode y' = y\n"
    "    ode y'' + y = 0\n"
    "    ode y' = y, y(0)=1\n"
    "\n"
    "what you can type:\n"
    "  dy/dx = y\n"
    "  y' = y\n"
    "  \\frac{dy}{dx} = y\n"
    "\n"
    "internal equivalent (advanced):\n"
    "  dsolve(Eq(d(y(x), x), y(x)), y(x))\n"
    "\n"
    "notes:\n"
    "  Eq(...) is equation form (not assignment)\n"
    "  y(x) means dependent function notation required by dsolve\n"
)
TUTORIAL_STEPS = (
    "step 1/6\n  run: 1/3 + 1/6\n  expect: 1/2",
    "step 2/6\n  run: d(x^3 + 2*x, x)\n  expect: 3*x**2 + 2",
    "step 3/6\n  run: int(sin(x), x)\n  expect: -cos(x)",
    "step 4/6\n  run: dy/dx = y\n  expect: Eq(y(x), Derivative(y(x), x))",
    "step 5/6\n  run: dsolve(Eq(d(y(x), x), y(x)), y(x))\n  expect: Eq(y(x), C1*exp(x))",
    "step 6/6\n  run: --latex d(x^2, x)\n  expect: 2 x",
)
COLOR_MODES = {"auto", "always", "never"}
ANSI_COLORS = {
    "red": "\033[31m",
    "yellow": "\033[33m",
    "bold": "\033[1m",
}
ANSI_RESET = "\033[0m"


def _wolframalpha_url(expr: str) -> str:
    return f"https://www.wolframalpha.com/input?i={quote_plus(expr)}"


def _is_complex_expression(expr: str) -> bool:
    if len(expr) >= 40:
        return True
    markers = ("d(", "int(", "solve(", "dsolve(", "Eq(", "ln(", "log(", "^", "{", "}", "e^{")
    return any(marker in expr for marker in markers)


def _format_clickable_link(label: str, url: str) -> str:
    if not sys.stderr.isatty() or os.getenv("TERM") == "dumb":
        return url
    esc = "\033"
    return f"{esc}]8;;{url}{esc}\\{label}{esc}]8;;{esc}\\"


def _should_use_color(stream, color_mode: str) -> bool:
    if color_mode not in COLOR_MODES:
        return False
    if color_mode == "never":
        return False
    if color_mode == "always":
        return True
    if os.getenv("NO_COLOR") is not None:
        return False
    if os.getenv("TERM") == "dumb":
        return False
    return stream.isatty()


def _style(text: str, *, color: str, stream, color_mode: str) -> str:
    if not _should_use_color(stream, color_mode):
        return text
    code = ANSI_COLORS.get(color)
    if code is None:
        return text
    return f"{code}{text}{ANSI_RESET}"


def _copy_to_clipboard(text: str) -> bool:
    commands = (
        ["pbcopy"],
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["clip"],
    )
    for cmd in commands:
        if shutil.which(cmd[0]) is None:
            continue
        try:
            subprocess.run(cmd, input=text, text=True, check=True, capture_output=True)
            return True
        except Exception:
            continue
    return False


def _print_wolfram_hint(expr: str, copy_link: bool = False, color_mode: str = "auto") -> None:
    url = _wolframalpha_url(expr)
    # Always print raw URL for maximum terminal compatibility (e.g., iTerm2 auto-linking).
    print(
        _style(f"hint: try WolframAlpha: {url}", color="yellow", stream=sys.stderr, color_mode=color_mode),
        file=sys.stderr,
    )
    if copy_link:
        if _copy_to_clipboard(url):
            print(
                _style("hint: WolframAlpha link copied to clipboard", color="yellow", stream=sys.stderr, color_mode=color_mode),
                file=sys.stderr,
            )
        else:
            print(
                _style("hint: clipboard copy unavailable on this system", color="yellow", stream=sys.stderr, color_mode=color_mode),
                file=sys.stderr,
            )


def _print_error(
    exc: Exception,
    expr: str | None = None,
    color_mode: str = "auto",
    session_locals: dict | None = None,
) -> None:
    print(_style(f"E: {exc}", color="red", stream=sys.stderr, color_mode=color_mode), file=sys.stderr)
    hint = _hint_for_error(str(exc), expr=expr, session_locals=session_locals)
    if hint:
        print(_style(f"hint: {hint}", color="yellow", stream=sys.stderr, color_mode=color_mode), file=sys.stderr)
    if expr and should_print_wolfram_hint(exc):
        _print_wolfram_hint(expr, color_mode=color_mode)


def _print_relaxed_rewrite_hints(expr: str, relaxed: bool, color_mode: str) -> None:
    for message in relaxed_rewrite_messages(expr, relaxed):
        print(
            _style(
                f"hint: {message}",
                color="yellow",
                stream=sys.stderr,
                color_mode=color_mode,
            ),
            file=sys.stderr,
        )


def _print_parse_explanation(expr: str, relaxed: bool, enabled: bool, color_mode: str) -> None:
    message = parse_explanation(expr, relaxed, enabled)
    if not message:
        return
    print(_style(f"hint: {message}", color="yellow", stream=sys.stderr, color_mode=color_mode), file=sys.stderr)


def _format_result(value, format_mode: str) -> str:
    if format_mode == "plain":
        return str(value)
    if format_mode == "pretty":
        from sympy import pretty as to_pretty

        return to_pretty(value)
    rendered = to_latex(value)
    if format_mode == "latex-inline":
        return f"${rendered}$"
    if format_mode == "latex-block":
        return f"$$\n{rendered}\n$$"
    return rendered


def _format_json_result(expr: str, relaxed: bool, value) -> str:
    normalized = normalize_expression(expr, relaxed=relaxed)
    payload = {"input": expr, "parsed": normalized, "result": str(value)}
    return dumps(payload, separators=(",", ":"))


def _render_value(value, *, format_mode: str, expr: str, relaxed: bool, parsed_expr: str | None = None) -> str:
    if format_mode == "json":
        if parsed_expr is None:
            return _format_json_result(expr, relaxed, value)
        payload = {"input": expr, "parsed": parsed_expr, "result": str(value)}
        return dumps(payload, separators=(",", ":"))
    return _format_result(value, format_mode)


def _split_top_level_commas(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            piece = "".join(current).strip()
            if piece:
                parts.append(piece)
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _infer_ode_dependent(eq_value: Eq):
    candidates = sorted(eq_value.atoms(AppliedUndef), key=str)
    if not candidates:
        return None
    return candidates[0]


def _evaluate_ode_alias(
    expr: str,
    *,
    relaxed: bool,
    simplify_output: bool,
    session_locals: dict | None = None,
):
    body = expr[4:].strip()
    if not body:
        raise ValueError("ode expects an equation, e.g. ode y' = y")

    pieces = _split_top_level_commas(body)
    if not pieces:
        raise ValueError("ode expects an equation, e.g. ode y' = y")
    equation_text, ic_texts = pieces[0], pieces[1:]

    eq_value = evaluate(
        equation_text,
        relaxed=relaxed,
        session_locals=session_locals,
        simplify_output=simplify_output,
    )
    if not isinstance(eq_value, Eq):
        raise ValueError("ode expects an equation, e.g. ode y' = y")

    dep = _infer_ode_dependent(eq_value)
    if dep is None:
        raise ValueError("could not infer dependent function; use y(x)-style notation")

    ics: dict = {}
    for ic_text in ic_texts:
        ic_value = evaluate(
            ic_text,
            relaxed=relaxed,
            session_locals=session_locals,
            simplify_output=simplify_output,
        )
        if not isinstance(ic_value, Eq):
            raise ValueError(f"initial condition must be an equation: {ic_text}")
        ics[ic_value.lhs] = ic_value.rhs

    if ics:
        result = dsolve(eq_value, dep, ics=ics)
        ics_rendered = ", ".join(f"{lhs}: {rhs}" for lhs, rhs in ics.items())
        parsed_expr = f"dsolve({eq_value}, {dep}, ics={{{ics_rendered}}})"
    else:
        result = dsolve(eq_value, dep)
        parsed_expr = f"dsolve({eq_value}, {dep})"
    return result, parsed_expr


def _latest_pypi_version() -> str | None:
    url = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
    try:
        with urlopen(url, timeout=2.0) as response:
            payload = loads(response.read().decode("utf-8"))
        return payload.get("info", {}).get("version")
    except (OSError, URLError, TimeoutError, ValueError, JSONDecodeError):
        return None


def _print_update_status() -> None:
    if VERSION == "dev":
        print("current version: dev (local checkout)")
        print("latest version: unknown from local checkout")
        print("install latest local changes with: uv tool install --force --reinstall --refresh .")
        return

    latest = _latest_pypi_version()
    print(f"current version: {VERSION}")
    if latest is None:
        print("latest version: unavailable (offline or PyPI unreachable)")
    elif latest == VERSION:
        print(f"latest version: {latest} (up to date)")
    else:
        print(f"latest version: {latest} (update available)")
    print(f"update with: {UPDATE_CMD}")


def _print_repl_startup_update_status() -> None:
    # Only auto-check when actually interactive to avoid noisy/non-deterministic
    # behavior in piped/scripted REPL sessions.
    if not sys.stdin.isatty():
        return
    if VERSION == "dev":
        print("startup update check: dev (local checkout)")
        return

    latest = _latest_pypi_version()
    if latest is None:
        print("startup update check: latest version unavailable")
    elif latest == VERSION:
        print(f"startup update check: v{VERSION} is up to date")
    else:
        print(f"startup update check: v{latest} available (you have v{VERSION})")
        print(f"update with: {UPDATE_CMD}")


def _parse_options(args: list[str]) -> CLIOptions:
    format_mode = "plain"
    relaxed = True
    simplify_output = True
    explain_parse = False
    always_wa = False
    copy_wa = False
    color_mode = "auto"
    idx = 0
    while idx < len(args) and args[idx].startswith("-"):
        arg = args[idx]
        if arg in {"-h", "--help"}:
            print(HELP_TEXT)
            raise SystemExit(0)
        if arg == "--format":
            if idx + 1 >= len(args):
                raise ValueError("missing value for --format")
            mode = args[idx + 1]
            if mode not in FORMAT_MODES:
                raise ValueError(f"unknown format mode: {mode}")
            format_mode = mode
            idx += 2
            continue
        if arg.startswith("--format="):
            mode = arg.split("=", 1)[1]
            if mode not in FORMAT_MODES:
                raise ValueError(f"unknown format mode: {mode}")
            format_mode = mode
            idx += 1
            continue
        if arg == "--latex":
            format_mode = "latex"
            idx += 1
            continue
        if arg == "--latex-inline":
            format_mode = "latex-inline"
            idx += 1
            continue
        if arg == "--latex-block":
            format_mode = "latex-block"
            idx += 1
            continue
        if arg == "--strict":
            relaxed = False
            idx += 1
            continue
        if arg == "--no-simplify":
            simplify_output = False
            idx += 1
            continue
        if arg == "--explain-parse":
            explain_parse = True
            idx += 1
            continue
        if arg == "--wa":
            always_wa = True
            idx += 1
            continue
        if arg == "--copy-wa":
            copy_wa = True
            idx += 1
            continue
        if arg == "--color":
            if idx + 1 >= len(args):
                raise ValueError("missing value for --color")
            mode = args[idx + 1]
            if mode not in COLOR_MODES:
                raise ValueError(f"unknown color mode: {mode}")
            color_mode = mode
            idx += 2
            continue
        if arg.startswith("--color="):
            mode = arg.split("=", 1)[1]
            if mode not in COLOR_MODES:
                raise ValueError(f"unknown color mode: {mode}")
            color_mode = mode
            idx += 1
            continue
        if arg == "--":
            idx += 1
            break
        if arg.startswith("--"):
            raise ValueError(f"unknown option: {arg}")
        break
    return CLIOptions(
        format_mode=format_mode,
        relaxed=relaxed,
        simplify_output=simplify_output,
        explain_parse=explain_parse,
        always_wa=always_wa,
        copy_wa=copy_wa,
        color_mode=color_mode,
        remaining=tuple(args[idx:]),
    )


def _handle_repl_command(expr: str, color_mode: str = "auto") -> bool:
    if expr in {":q", ":quit", ":x"}:
        raise EOFError
    if expr in {":h", ":help"}:
        print(HELP_TEXT)
        return True
    if expr == ":examples":
        print(EXAMPLES_TEXT)
        return True
    if expr in {":tutorial", ":tour"}:
        print(TUTORIAL_TEXT)
        return True
    if expr == ":ode":
        print(ODE_TEXT)
        return True
    if expr in {":v", ":version"}:
        print(f"{CLI_NAME} v{VERSION}")
        return True
    if expr in {":update", ":check"}:
        _print_update_status()
        return True
    if expr.startswith(":"):
        print(_style("E: unknown command", color="red", stream=sys.stderr, color_mode=color_mode), file=sys.stderr)
        print(
            _style("hint: use :h to list commands", color="yellow", stream=sys.stderr, color_mode=color_mode),
            file=sys.stderr,
        )
        return True
    return False


def _print_tutorial_step(index: int) -> None:
    print(TUTORIAL_STEPS[index])


def _tutorial_command(expr: str, state: dict | None) -> bool:
    if state is None:
        return False
    if expr in {":tutorial", ":tour"}:
        state["active"] = True
        state["index"] = 0
        print("tutorial mode started. use :next, :repeat, :done")
        _print_tutorial_step(state["index"])
        return True
    if expr == ":next":
        if not state.get("active", False):
            print("hint: start with :tutorial", file=sys.stderr)
            return True
        nxt = state["index"] + 1
        if nxt >= len(TUTORIAL_STEPS):
            print("tutorial complete. use :done to exit tutorial mode")
            return True
        state["index"] = nxt
        _print_tutorial_step(state["index"])
        return True
    if expr == ":repeat":
        if not state.get("active", False):
            print("hint: start with :tutorial", file=sys.stderr)
            return True
        _print_tutorial_step(state["index"])
        return True
    if expr == ":done":
        if state.get("active", False):
            state["active"] = False
            print("tutorial mode ended")
        else:
            print("hint: tutorial is not active; use :tutorial", file=sys.stderr)
        return True
    return False


def _try_parse_repl_inline_options(expr: str):
    line = expr.strip()
    if line.startswith(f"{CLI_NAME} "):
        line = line[len(CLI_NAME) :].strip()
    elif not line.startswith("-"):
        return None
    try:
        tokens = shlex.split(line)
    except ValueError as exc:
        raise ValueError(f"invalid REPL option input: {exc}") from exc
    return _parse_options(tokens)


def _execute_expression(
    expr: str,
    *,
    format_mode: str,
    relaxed: bool,
    simplify_output: bool,
    explain_parse: bool,
    always_wa: bool,
    copy_wa: bool,
    color_mode: str,
    session_locals: dict | None = None,
) -> None:
    is_ode_alias = expr.strip().lower().startswith("ode ")
    if is_ode_alias:
        value, parsed_expr = _evaluate_ode_alias(
            expr,
            relaxed=relaxed,
            simplify_output=simplify_output,
            session_locals=session_locals,
        )
        if explain_parse:
            print(_style(f"hint: parsed as: {parsed_expr}", color="yellow", stream=sys.stderr, color_mode=color_mode), file=sys.stderr)
        if format_mode == "plain" and isinstance(value, Eq):
            rendered = f"{value.lhs} = {value.rhs}"
        else:
            rendered = _render_value(
                value,
                format_mode=format_mode,
                expr=expr,
                relaxed=relaxed,
                parsed_expr=parsed_expr,
            )
    else:
        _print_relaxed_rewrite_hints(expr, relaxed, color_mode)
        _print_parse_explanation(expr, relaxed, explain_parse, color_mode)
        value = evaluate(
            expr,
            relaxed=relaxed,
            session_locals=session_locals,
            simplify_output=simplify_output,
        )
        rendered = _render_value(value, format_mode=format_mode, expr=expr, relaxed=relaxed)
    print(rendered)
    if always_wa or _is_complex_expression(expr):
        _print_wolfram_hint(expr, copy_link=copy_wa, color_mode=color_mode)


def run(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    try:
        options = _parse_options(args)
    except SystemExit:
        return 0
    except Exception as exc:
        _print_error(exc, color_mode="auto")
        return 1

    format_mode = options.format_mode
    relaxed = options.relaxed
    simplify_output = options.simplify_output
    explain_parse = options.explain_parse
    always_wa = options.always_wa
    copy_wa = options.copy_wa
    color_mode = options.color_mode
    remaining = list(options.remaining)

    if remaining:
        expr = " ".join(remaining)
        if expr == ":examples":
            print(EXAMPLES_TEXT)
            return 0
        if expr == ":ode":
            print(ODE_TEXT)
            return 0
        if expr in {":tutorial", ":tour"}:
            print(TUTORIAL_TEXT)
            return 0
        if expr in {":v", ":version"}:
            print(f"{CLI_NAME} v{VERSION}")
            return 0
        if expr in {":update", ":check"}:
            _print_update_status()
            return 0
        try:
            _execute_expression(
                expr,
                format_mode=format_mode,
                relaxed=relaxed,
                simplify_output=simplify_output,
                explain_parse=explain_parse,
                always_wa=always_wa,
                copy_wa=copy_wa,
                color_mode=color_mode,
            )
            return 0
        except Exception as exc:
            _print_error(exc, expr, color_mode=color_mode)
            return 1

    print(f"{CLI_NAME} v{VERSION} REPL. :h help, :q quit, Ctrl-D exit.")
    print(f"update: {UPDATE_CMD}")
    _print_repl_startup_update_status()
    session_locals: dict = {}
    repl_format_mode = format_mode
    repl_relaxed = relaxed
    repl_simplify_output = simplify_output
    repl_explain_parse = explain_parse
    repl_always_wa = always_wa
    repl_copy_wa = copy_wa
    repl_color_mode = color_mode
    tutorial_state = {"active": False, "index": 0}
    expr: str | None = None
    while True:
        try:
            expr = input(PROMPT).strip()
            if not expr:
                continue
            if _tutorial_command(expr, tutorial_state):
                continue
            if _handle_repl_command(expr, color_mode=repl_color_mode):
                continue
            parsed_inline = _try_parse_repl_inline_options(expr)
            if parsed_inline is not None:
                repl_format_mode = parsed_inline.format_mode
                repl_relaxed = parsed_inline.relaxed
                repl_simplify_output = parsed_inline.simplify_output
                repl_explain_parse = parsed_inline.explain_parse
                repl_always_wa = parsed_inline.always_wa
                repl_copy_wa = parsed_inline.copy_wa
                repl_color_mode = parsed_inline.color_mode
                if not parsed_inline.remaining:
                    print("hint: REPL options updated for this session", file=sys.stderr)
                    continue
                expr = " ".join(parsed_inline.remaining)
            _execute_expression(
                expr,
                format_mode=repl_format_mode,
                relaxed=repl_relaxed,
                simplify_output=repl_simplify_output,
                explain_parse=repl_explain_parse,
                always_wa=repl_always_wa,
                copy_wa=repl_copy_wa,
                color_mode=repl_color_mode,
                session_locals=session_locals,
            )
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        except Exception as exc:
            _print_error(exc, expr=expr, color_mode=repl_color_mode, session_locals=session_locals)


if __name__ == "__main__":
    raise SystemExit(run())
