from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version as package_version
from urllib.parse import quote_plus
from urllib.request import urlopen

from sympy import Eq
from sympy.matrices.matrixbase import MatrixBase

from .core import evaluate, normalize_expression
from .diagnostics import (
    hint_for_error as _hint_for_error,
    parse_explanation,
    relaxed_rewrite_messages,
    should_print_wolfram_hint,
)
from .options import COLOR_MODES, CLIOptions, parse_options
from .ode import (
    evaluate_ode_alias as evaluate_ode_alias_impl,
    infer_ode_dependent as infer_ode_dependent_impl,
    split_top_level_commas as split_top_level_commas_impl,
)
from .repl import (
    handle_repl_command as handle_repl_command_impl,
    try_parse_repl_inline_options as try_parse_repl_inline_options_impl,
    tutorial_command as tutorial_command_impl,
)
from .render import (
    format_json_result as format_json_result_impl,
    format_result as format_result_impl,
    render_value as render_value_impl,
)
from .updates import (
    compare_versions as _compare_versions_impl,
    latest_pypi_version as _latest_pypi_version_impl,
    repl_startup_update_status_lines,
    update_status_lines,
)

PACKAGE_NAME = "philcalc"
CLI_NAME = "phil"
UPDATE_CMD = "uv tool upgrade philcalc"


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
    "  ?, ??, ???     progressive help chain (discover more features)\n"
    "  :examples      show example expressions\n"
    "  :tutorial      show guided tour for new users\n"
    "  :ode           show ODE quick reference and templates\n"
    "  :linalg, :la   show linear algebra quick reference and templates\n"
    "  :next          next tutorial step (after :tutorial)\n"
    "  :repeat        repeat current tutorial step\n"
    "  :done          exit tutorial mode\n"
    "  :v, :version   show version\n"
    "  :update, :check  check current vs latest version\n"
    "  :q, :quit, :x  quit\n"
    "\n"
    "quick examples:\n"
    "  (1 - 25e^5)e^{-5t} + (25e^5 - 1)t e^{-5t} + t e^{-5t} ln(t)\n"
    "  10^100000 + 1 - 10^100000\n"
    "  sin^2(x) + cos^2(x)\n"
    "  msolve(Matrix([[2,1],[1,3]]), Matrix([1,2]))\n"
    "  d(x^3 + 2*x, x)\n"
    "  int(sin(x), x)\n"
    "  solve(x^2 - 4, x)\n"
    "  N(pi, 20)"
)
HELP_CHAIN_TEXT = (
    "help chain:\n"
    "  ?    = standard help\n"
    "  ??   = power-user shortcuts\n"
    "  ???  = capability demos\n"
)
HELP_POWER_TEXT = (
    "power-user shortcuts:\n"
    "  use inline REPL options: --latex d(x^2, x)\n"
    "  inspect parser rewrites: --explain-parse 'sinx'\n"
    "  machine-readable output: --format json 'sinx'\n"
    "  fast ODE solve alias: ode y' = y, y(0)=1\n"
    "  session memory: ans + 1, A = Matrix([[1,2],[3,4]])\n"
    "hint: try ??? for capability demos"
)
HELP_DEMO_TEXT = (
    "capability demos:\n"
    "  exact huge integer arithmetic:\n"
    "    10^100000 + 1 - 10^100000\n"
    "    -> 1\n"
    "  exact rational arithmetic:\n"
    "    1/3 + 1/6\n"
    "    -> 1/2\n"
    "  symbolic workflow:\n"
    "    d(x^3 + 2*x, x), int(sin(x), x), solve(x^2 - 4, x)\n"
)
EXAMPLES_TEXT = (
    "examples:\n"
    "  1/3 + 1/6\n"
    "  10^100000 + 1 - 10^100000\n"
    "  sin^2(x) + cos^2(x)\n"
    "  msolve(Matrix([[2,1],[1,3]]), Matrix([1,2]))\n"
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
    "  7) Exactness demo: phil '10^100000 + 1 - 10^100000'\n"
    "  8) Use :examples and ? / ?? / ??? for more patterns\n"
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
LINALG_TEXT = (
    "linear algebra quick reference:\n"
    "  quick start:\n"
    "    linalg solve A=[[2,1],[1,3]] b=[1,2]\n"
    "    linalg rref A=[[1,2],[2,4]]\n"
    "    msolve(Matrix([[2,1],[1,3]]), Matrix([1,2]))\n"
    "    rref(Matrix([[1,2],[2,4]]))\n"
    "    nullspace(Matrix([[1,2],[2,4]]))\n"
    "\n"
    "symbolic systems:\n"
    "  linsolve((Eq(2*x + y, 1), Eq(x + 3*y, 2)), (x, y))\n"
    "\n"
    "notes:\n"
    "  use Matrix([...]) for vectors and matrices\n"
    "  msolve(A, b) expects square, invertible A for LUsolve\n"
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
    return format_result_impl(value, format_mode)


def _format_json_result(expr: str, relaxed: bool, value) -> str:
    return format_json_result_impl(
        expr,
        relaxed,
        value,
        normalize_expression_fn=normalize_expression,
    )


def _render_value(value, *, format_mode: str, expr: str, relaxed: bool, parsed_expr: str | None = None) -> str:
    return render_value_impl(
        value,
        format_mode=format_mode,
        expr=expr,
        relaxed=relaxed,
        normalize_expression_fn=normalize_expression,
        parsed_expr=parsed_expr,
    )


def _split_top_level_commas(text: str) -> list[str]:
    return split_top_level_commas_impl(text)


def _infer_ode_dependent(eq_value: Eq):
    return infer_ode_dependent_impl(eq_value)


def _evaluate_ode_alias(
    expr: str,
    *,
    relaxed: bool,
    simplify_output: bool,
    session_locals: dict | None = None,
):
    return evaluate_ode_alias_impl(
        expr,
        evaluate_fn=evaluate,
        relaxed=relaxed,
        simplify_output=simplify_output,
        session_locals=session_locals,
    )


def _consume_bracket_literal(text: str, start: int) -> tuple[str, int]:
    if start >= len(text) or text[start] != "[":
        raise ValueError("expected bracketed literal like [[...]]")
    depth = 0
    idx = start
    while idx < len(text):
        ch = text[idx]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1], idx + 1
        idx += 1
    raise ValueError("unclosed bracket literal; expected closing ']'")


def _parse_linalg_keyed_literals(text: str, required_keys: set[str]) -> dict[str, str]:
    idx = 0
    parsed: dict[str, str] = {}
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        key_start = idx
        while idx < len(text) and text[idx].isalpha():
            idx += 1
        key = text[key_start:idx]
        if key not in required_keys:
            expected = ", ".join(sorted(required_keys))
            raise ValueError(f"unknown linalg parameter '{key}'; expected: {expected}")
        if key in parsed:
            raise ValueError(f"duplicate linalg parameter '{key}'")
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text) or text[idx] != "=":
            raise ValueError(f"linalg parameter '{key}' must use '='")
        idx += 1
        while idx < len(text) and text[idx].isspace():
            idx += 1
        literal, idx = _consume_bracket_literal(text, idx)
        parsed[key] = literal

    missing = sorted(required_keys - set(parsed))
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"missing linalg parameter(s): {missing_text}")
    return parsed


def _evaluate_linalg_alias(
    expr: str,
    *,
    relaxed: bool,
    simplify_output: bool,
    session_locals: dict | None = None,
):
    body = expr[7:].strip()
    if not body:
        raise ValueError("linalg expects a subcommand: solve or rref")
    pieces = body.split(maxsplit=1)
    subcommand = pieces[0].lower()
    rest = pieces[1] if len(pieces) > 1 else ""

    if subcommand == "solve":
        params = _parse_linalg_keyed_literals(rest, {"A", "b"})
        matrix_text = params["A"]
        rhs_text = params["b"]
        matrix_value = evaluate(
            f"Matrix({matrix_text})",
            relaxed=relaxed,
            session_locals=session_locals,
            simplify_output=simplify_output,
        )
        rhs_value = evaluate(
            f"Matrix({rhs_text})",
            relaxed=relaxed,
            session_locals=session_locals,
            simplify_output=simplify_output,
        )
        if not isinstance(matrix_value, MatrixBase) or not isinstance(rhs_value, MatrixBase):
            raise ValueError("linalg solve expects matrix literals for A and b")
        if matrix_value.rows != matrix_value.cols:
            raise ValueError("linalg solve expects square A")
        if rhs_value.cols != 1:
            raise ValueError("linalg solve expects b as a column vector, e.g. b=[1,2]")
        if rhs_value.rows != matrix_value.rows:
            raise ValueError("linalg solve expects len(b) to match rows of A")
        result = matrix_value.LUsolve(rhs_value)
        parsed_expr = f"msolve(Matrix({matrix_text}), Matrix({rhs_text}))"
        return result, parsed_expr

    if subcommand == "rref":
        params = _parse_linalg_keyed_literals(rest, {"A"})
        matrix_text = params["A"]
        matrix_value = evaluate(
            f"Matrix({matrix_text})",
            relaxed=relaxed,
            session_locals=session_locals,
            simplify_output=simplify_output,
        )
        if not isinstance(matrix_value, MatrixBase):
            raise ValueError("linalg rref expects a matrix literal for A")
        result = matrix_value.rref()
        parsed_expr = f"rref(Matrix({matrix_text}))"
        return result, parsed_expr

    raise ValueError("unknown linalg subcommand; use 'solve' or 'rref'")


def _latest_pypi_version() -> str | None:
    return _latest_pypi_version_impl(PACKAGE_NAME, urlopen_fn=urlopen)


def _compare_versions(current: str, latest: str) -> int | None:
    return _compare_versions_impl(current, latest)


def _print_update_status() -> None:
    latest = None if VERSION == "dev" else _latest_pypi_version()
    lines = update_status_lines(
        VERSION,
        latest,
        UPDATE_CMD,
        compare_fn=_compare_versions,
    )
    for line in lines:
        print(line)


def _print_repl_startup_update_status() -> None:
    # Only auto-check when actually interactive to avoid noisy/non-deterministic
    # behavior in piped/scripted REPL sessions.
    if not sys.stdin.isatty():
        return
    latest = None if VERSION == "dev" else _latest_pypi_version()
    lines = repl_startup_update_status_lines(
        VERSION,
        latest,
        UPDATE_CMD,
        compare_fn=_compare_versions,
    )
    for line in lines:
        print(line)


def _parse_options(args: list[str]) -> CLIOptions:
    return parse_options(args, help_text=HELP_TEXT)


def _handle_repl_command(expr: str, color_mode: str = "auto") -> bool:
    return handle_repl_command_impl(
        expr,
        help_text=HELP_TEXT,
        help_chain_text=HELP_CHAIN_TEXT,
        help_power_text=HELP_POWER_TEXT,
        help_demo_text=HELP_DEMO_TEXT,
        examples_text=EXAMPLES_TEXT,
        tutorial_text=TUTORIAL_TEXT,
        ode_text=ODE_TEXT,
        linalg_text=LINALG_TEXT,
        cli_name=CLI_NAME,
        version=VERSION,
        print_update_status=_print_update_status,
        style_fn=_style,
        color_mode=color_mode,
        stderr=sys.stderr,
    )


def _print_tutorial_step(index: int) -> None:
    print(TUTORIAL_STEPS[index])


def _tutorial_command(expr: str, state: dict | None) -> bool:
    return tutorial_command_impl(
        expr,
        state,
        tutorial_steps=TUTORIAL_STEPS,
        print_tutorial_step=_print_tutorial_step,
        stderr=sys.stderr,
    )


def _try_parse_repl_inline_options(expr: str):
    return try_parse_repl_inline_options_impl(
        expr,
        cli_name=CLI_NAME,
        parse_options_fn=_parse_options,
    )


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
    is_linalg_alias = expr.strip().lower().startswith("linalg ")
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
    elif is_linalg_alias:
        value, parsed_expr = _evaluate_linalg_alias(
            expr,
            relaxed=relaxed,
            simplify_output=simplify_output,
            session_locals=session_locals,
        )
        if explain_parse:
            print(_style(f"hint: parsed as: {parsed_expr}", color="yellow", stream=sys.stderr, color_mode=color_mode), file=sys.stderr)
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
        if expr == "?":
            print(HELP_TEXT)
            print(HELP_CHAIN_TEXT)
            return 0
        if expr == "??":
            print(HELP_POWER_TEXT)
            return 0
        if expr == "???":
            print(HELP_DEMO_TEXT)
            return 0
        if expr == ":examples":
            print(EXAMPLES_TEXT)
            return 0
        if expr == ":ode":
            print(ODE_TEXT)
            return 0
        if expr in {":linalg", ":la"}:
            print(LINALG_TEXT)
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
