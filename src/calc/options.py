from __future__ import annotations

from dataclasses import dataclass

FORMAT_MODES = ("plain", "pretty", "latex", "latex-inline", "latex-block", "json")
COLOR_MODES = {"auto", "always", "never"}


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


def parse_options(args: list[str], *, help_text: str) -> CLIOptions:
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
            print(help_text)
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
