from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version as package_version
from urllib.parse import quote_plus

from sympy import latex as to_latex

from .core import evaluate

PACKAGE_NAME = "calc-cli"


def _calc_version() -> str:
    try:
        return package_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "dev"


VERSION = _calc_version()
PROMPT = "calc> "
HELP_TEXT = (
    f"calc v{VERSION} - symbolic CLI calculator\n"
    "\n"
    "usage:\n"
    "  calc [--latex] [--strict] [--wa] [--copy-wa] '<expression>'\n"
    "  calc\n"
    "  calc :examples\n"
    "\n"
    "options:\n"
    "  --latex         print result as LaTeX\n"
    "  --strict        disable relaxed input parsing\n"
    "  --wa            always print WolframAlpha equivalent link\n"
    "  --copy-wa       copy WolframAlpha link to clipboard when shown\n"
    "\n"
    "upgrade:\n"
    "  uv tool upgrade calc-cli\n"
    "\n"
    "repl commands:\n"
    "  :h, :help      show this help\n"
    "  :examples      show example expressions\n"
    "  :v, :version   show version\n"
    "  :update        show update command\n"
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


def _print_wolfram_hint(expr: str, copy_link: bool = False) -> None:
    url = _wolframalpha_url(expr)
    clickable = _format_clickable_link("Open WolframAlpha", url)
    print(f"hint: try WolframAlpha: {clickable}", file=sys.stderr)
    if copy_link:
        if _copy_to_clipboard(url):
            print("hint: WolframAlpha link copied to clipboard", file=sys.stderr)
        else:
            print("hint: clipboard copy unavailable on this system", file=sys.stderr)


def _print_error(exc: Exception, expr: str | None = None) -> None:
    print(f"E: {exc}", file=sys.stderr)
    hint = _hint_for_error(str(exc))
    if hint:
        print(f"hint: {hint}", file=sys.stderr)
    if expr:
        _print_wolfram_hint(expr)


def _hint_for_error(message: str) -> str | None:
    text = message.lower()
    if "unexpected eof" in text:
        return "check missing closing ')' or unmatched quote"
    if "name '" in text and "is not defined" in text:
        return "use one of: x y z t pi e f and documented functions"
    if "blocked token" in text:
        return "remove blocked patterns like '__', ';', or newlines"
    if "empty expression" in text:
        return "enter a math expression, or use :examples"
    return None


def _format_result(value, latex_output: bool) -> str:
    if not latex_output:
        return str(value)
    return to_latex(value)


def _parse_options(args: list[str]) -> tuple[bool, bool, bool, bool, list[str]]:
    latex_output = False
    relaxed = True
    always_wa = False
    copy_wa = False
    idx = 0
    while idx < len(args) and args[idx].startswith("-"):
        arg = args[idx]
        if arg in {"-h", "--help"}:
            print(HELP_TEXT)
            raise SystemExit(0)
        if arg == "--latex":
            latex_output = True
            idx += 1
            continue
        if arg == "--strict":
            relaxed = False
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
        if arg == "--":
            idx += 1
            break
        if arg.startswith("--"):
            raise ValueError(f"unknown option: {arg}")
        break
    return latex_output, relaxed, always_wa, copy_wa, args[idx:]


def _handle_repl_command(expr: str) -> bool:
    if expr in {":q", ":quit", ":x"}:
        raise EOFError
    if expr in {":h", ":help"}:
        print(HELP_TEXT)
        return True
    if expr == ":examples":
        print(EXAMPLES_TEXT)
        return True
    if expr in {":v", ":version"}:
        print(f"calc v{VERSION}")
        return True
    if expr == ":update":
        print("update with: uv tool upgrade calc-cli")
        return True
    if expr.startswith(":"):
        print("E: unknown command", file=sys.stderr)
        print("hint: use :h to list commands", file=sys.stderr)
        return True
    return False


def run(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    try:
        latex_output, relaxed, always_wa, copy_wa, remaining = _parse_options(args)
    except SystemExit:
        return 0
    except Exception as exc:
        _print_error(exc)
        return 1

    if remaining:
        expr = " ".join(remaining)
        if expr == ":examples":
            print(EXAMPLES_TEXT)
            return 0
        if expr in {":v", ":version"}:
            print(f"calc v{VERSION}")
            return 0
        if expr == ":update":
            print("update with: uv tool upgrade calc-cli")
            return 0
        try:
            print(_format_result(evaluate(expr, relaxed=relaxed), latex_output))
            if always_wa or _is_complex_expression(expr):
                _print_wolfram_hint(expr, copy_link=copy_wa)
            return 0
        except Exception as exc:
            _print_error(exc, expr)
            return 1

    print(f"calc v{VERSION} REPL. :h help, :q quit, Ctrl-D exit.")
    print("update: uv tool upgrade calc-cli")
    while True:
        try:
            expr = input(PROMPT).strip()
            if not expr:
                continue
            if _handle_repl_command(expr):
                continue
            print(_format_result(evaluate(expr, relaxed=True), latex_output))
            if always_wa or _is_complex_expression(expr):
                _print_wolfram_hint(expr, copy_link=copy_wa)
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        except Exception as exc:
            _print_error(exc, expr)


if __name__ == "__main__":
    raise SystemExit(run())
