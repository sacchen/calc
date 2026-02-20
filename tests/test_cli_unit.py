import runpy
from types import SimpleNamespace

import pytest

import calc.cli as cli


def test_parse_options_help_exits(capsys):
    with pytest.raises(SystemExit):
        cli._parse_options(["--help"])
    out = capsys.readouterr().out
    assert "usage:" in out


def test_parse_options_unknown_raises():
    with pytest.raises(ValueError, match="unknown option"):
        cli._parse_options(["--wat"])


def test_parse_options_flags():
    format_mode, relaxed, simplify_output, explain_parse, always_wa, copy_wa, color_mode, rest = cli._parse_options(
        ["--latex", "--strict", "--explain-parse", "--wa", "--copy-wa", "2+2"]
    )
    assert format_mode == "latex"
    assert relaxed is False
    assert simplify_output is True
    assert explain_parse is True
    assert always_wa is True
    assert copy_wa is True
    assert color_mode == "auto"
    assert rest == ["2+2"]


def test_parse_options_latex_modes():
    format_mode, *_ = cli._parse_options(["--latex-inline", "x"])
    assert format_mode == "latex-inline"
    format_mode, *_ = cli._parse_options(["--latex-block", "x"])
    assert format_mode == "latex-block"


def test_parse_options_format_and_no_simplify():
    format_mode, _, simplify_output, _, _, _, _, rest = cli._parse_options(
        ["--format", "pretty", "--no-simplify", "2+2"]
    )
    assert format_mode == "pretty"
    assert simplify_output is False
    assert rest == ["2+2"]


def test_parse_options_json_format():
    format_mode, *_ = cli._parse_options(["--format", "json", "x"])
    assert format_mode == "json"
    format_mode, *_ = cli._parse_options(["--format=json", "x"])
    assert format_mode == "json"


def test_parse_options_double_dash_and_single_dash_literal():
    _, _, _, _, _, _, _, rest = cli._parse_options(["--", "--not-an-option"])
    assert rest == ["--not-an-option"]
    _, _, _, _, _, _, _, rest = cli._parse_options(["-1"])
    assert rest == ["-1"]


def test_parse_options_color_modes():
    *_, color_mode, rest = cli._parse_options(["--color", "always", "2+2"])
    assert color_mode == "always"
    assert rest == ["2+2"]
    *_, color_mode, rest = cli._parse_options(["--color=never", "2+2"])
    assert color_mode == "never"
    assert rest == ["2+2"]


def test_parse_options_color_mode_errors():
    with pytest.raises(ValueError, match="missing value for --color"):
        cli._parse_options(["--color"])
    with pytest.raises(ValueError, match="unknown color mode"):
        cli._parse_options(["--color", "nope"])


def test_print_parse_explanation(capsys):
    cli._print_parse_explanation("sinx", relaxed=True, enabled=True, color_mode="never")
    err = capsys.readouterr().err
    assert "parsed as: sin(x)" in err


def test_hint_for_error_messages():
    assert "missing closing" in cli._hint_for_error("Unexpected EOF while parsing")
    assert "documented functions" in cli._hint_for_error("name 'a' is not defined")
    assert "derivative syntax" in cli._hint_for_error("invalid syntax", expr="d(sin(x)/dx")
    assert "matrix syntax" in cli._hint_for_error("invalid syntax", expr="Matrix([1,2],[3,4])")
    assert "Eq syntax" in cli._hint_for_error("invalid syntax", expr="Eq(d(y(x), x) y(x))")
    assert "dsolve expects an equation" in cli._hint_for_error("invalid syntax", expr="dsolve(d(y(x), x), y(x))")
    assert "LaTeX fraction syntax" in cli._hint_for_error("invalid syntax", expr=r"\frac{dy}{dx")
    assert "y(x)" in cli._hint_for_error("dsolve() and classify_ode() only work with functions of one variable, not y")
    assert "blocked patterns" in cli._hint_for_error("blocked token in expression")
    assert "enter a math expression" in cli._hint_for_error("empty expression")
    assert "reserved for function notation" in cli._hint_for_error("cannot assign reserved name: f")
    assert "reserved by phil internals" in cli._hint_for_error("cannot assign reserved name: sin")
    assert cli._hint_for_error("different error") is None


def test_is_complex_expression_heuristics():
    assert cli._is_complex_expression("x" * 40) is True
    assert cli._is_complex_expression("d(x^2, x)") is True
    assert cli._is_complex_expression("2+2") is False


def test_format_result_latex():
    assert cli._format_result("x", format_mode="plain") == "x"
    assert cli._format_result(2, format_mode="latex") == "2"
    assert cli._format_result(2, format_mode="latex-inline") == "$2$"
    assert cli._format_result(2, format_mode="latex-block") == "$$\n2\n$$"


def test_format_json_result():
    out = cli._format_json_result("sinx", relaxed=True, value="sin(x)")
    assert out == '{"input":"sinx","parsed":"sin(x)","result":"sin(x)"}'


def test_format_result_pretty():
    from sympy import Matrix

    out = cli._format_result(Matrix([[1, 2], [3, 4]]), format_mode="pretty")
    assert "1  2" in out


def test_format_clickable_link_tty(monkeypatch):
    monkeypatch.setattr(cli.sys.stderr, "isatty", lambda: True)
    monkeypatch.setenv("TERM", "xterm-256color")
    out = cli._format_clickable_link("Open", "https://example.com")
    assert "https://example.com" in out
    assert "\033]8;;" in out


def test_style_respects_color_mode(monkeypatch):
    monkeypatch.setattr(cli.sys.stderr, "isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert "\033[31m" in cli._style("E: fail", color="red", stream=cli.sys.stderr, color_mode="auto")
    assert "\033[31m" in cli._style("E: fail", color="red", stream=cli.sys.stderr, color_mode="always")
    assert "\033[31m" not in cli._style("E: fail", color="red", stream=cli.sys.stderr, color_mode="never")


def test_style_respects_no_color(monkeypatch):
    monkeypatch.setattr(cli.sys.stderr, "isatty", lambda: True)
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "xterm-256color")
    out = cli._style("hint", color="yellow", stream=cli.sys.stderr, color_mode="auto")
    assert "\033[33m" not in out


def test_copy_to_clipboard_success(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/bin/pbcopy" if name == "pbcopy" else None)
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0))
    assert cli._copy_to_clipboard("abc") is True


def test_copy_to_clipboard_failure(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    assert cli._copy_to_clipboard("abc") is False


def test_copy_to_clipboard_exception_then_fallback(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/bin/tool" if name == "pbcopy" else None)

    def boom(*args, **kwargs):
        raise RuntimeError("clipboard error")

    monkeypatch.setattr(cli.subprocess, "run", boom)
    assert cli._copy_to_clipboard("abc") is False


def test_latest_pypi_version_success(monkeypatch):
    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"info":{"version":"9.9.9"}}'

    monkeypatch.setattr(cli, "urlopen", lambda *a, **k: DummyResponse())
    assert cli._latest_pypi_version() == "9.9.9"


def test_latest_pypi_version_failure(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(cli, "urlopen", boom)
    assert cli._latest_pypi_version() is None


def test_print_update_status_dev(monkeypatch, capsys):
    monkeypatch.setattr(cli, "VERSION", "dev")
    cli._print_update_status()
    out = capsys.readouterr().out
    assert "local checkout" in out
    assert "install latest local changes" in out


def test_print_update_status_up_to_date(monkeypatch, capsys):
    monkeypatch.setattr(cli, "VERSION", "1.2.3")
    monkeypatch.setattr(cli, "_latest_pypi_version", lambda: "1.2.3")
    cli._print_update_status()
    out = capsys.readouterr().out
    assert "up to date" in out


def test_print_update_status_update_available(monkeypatch, capsys):
    monkeypatch.setattr(cli, "VERSION", "1.2.3")
    monkeypatch.setattr(cli, "_latest_pypi_version", lambda: "2.0.0")
    cli._print_update_status()
    out = capsys.readouterr().out
    assert "update available" in out


def test_print_update_status_latest_unavailable(monkeypatch, capsys):
    monkeypatch.setattr(cli, "VERSION", "1.2.3")
    monkeypatch.setattr(cli, "_latest_pypi_version", lambda: None)
    cli._print_update_status()
    out = capsys.readouterr().out
    assert "unavailable" in out


def test_calc_version_package_missing(monkeypatch):
    def boom(_):
        raise cli.PackageNotFoundError

    monkeypatch.setattr(cli, "package_version", boom)
    assert cli._calc_version() == "dev"


def test_run_one_shot_success(monkeypatch, capsys):
    monkeypatch.setattr(cli, "evaluate", lambda expr, **kwargs: 4)
    rc = cli.run(["2+2"])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip().endswith("4")


def test_run_one_shot_error(monkeypatch, capsys):
    def boom(expr, **kwargs):
        raise ValueError("empty expression")

    monkeypatch.setattr(cli, "evaluate", boom)
    rc = cli.run(["2+2"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "E: empty expression" in captured.err
    assert "try WolframAlpha" in captured.err


def test_run_one_shot_reserved_name_error_skips_wolfram_hint(monkeypatch, capsys):
    def boom(expr, **kwargs):
        raise ValueError("cannot assign reserved name: f")

    monkeypatch.setattr(cli, "evaluate", boom)
    rc = cli.run(["f = x^2"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "reserved for function notation" in captured.err
    assert "try WolframAlpha" not in captured.err


def test_run_repl_uses_strict_flag(monkeypatch, capsys):
    calls = []
    inputs = iter(["2x", ":q"])

    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    def fake_eval(expr, **kwargs):
        calls.append(kwargs.get("relaxed"))
        return "ok"

    monkeypatch.setattr(cli, "evaluate", fake_eval)
    rc = cli.run(["--strict"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "ok" in captured.out
    assert calls == [False]


def test_run_help_returns_zero(capsys):
    rc = cli.run(["--help"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "usage:" in out


def test_run_shortcut_commands(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_print_update_status", lambda: print("status"))
    assert cli.run([":examples"]) == 0
    assert cli.run([":tutorial"]) == 0
    assert cli.run([":ode"]) == 0
    assert cli.run([":version"]) == 0
    assert cli.run([":update"]) == 0
    out = capsys.readouterr().out
    assert "examples:" in out
    assert "guided tour:" in out
    assert "ode quick reference:" in out
    assert "phil v" in out
    assert "status" in out


def test_run_one_shot_prints_wa_when_forced(monkeypatch, capsys):
    monkeypatch.setattr(cli, "evaluate", lambda expr, **kwargs: 4)
    monkeypatch.setattr(
        cli,
        "_print_wolfram_hint",
        lambda expr, copy_link=False, color_mode="auto": print("WA", file=cli.sys.stderr),
    )
    rc = cli.run(["--wa", "2+2"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "WA" in err


def test_run_repl_empty_then_command(monkeypatch, capsys):
    inputs = iter(["", ":h", ":q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    rc = cli.run([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "repl commands:" in out


def test_run_repl_error_path(monkeypatch, capsys):
    inputs = iter(["2+2", ":q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    def boom(expr, **kwargs):
        raise ValueError("empty expression")

    monkeypatch.setattr(cli, "evaluate", boom)
    rc = cli.run([])
    err = capsys.readouterr().err
    assert rc == 0
    assert "E: empty expression" in err


def test_print_wolfram_hint_copy_branches(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_copy_to_clipboard", lambda text: True)
    cli._print_wolfram_hint("2+2", copy_link=True)
    err = capsys.readouterr().err
    assert "copied to clipboard" in err

    monkeypatch.setattr(cli, "_copy_to_clipboard", lambda text: False)
    cli._print_wolfram_hint("2+2", copy_link=True)
    err = capsys.readouterr().err
    assert "clipboard copy unavailable" in err


def test_handle_repl_commands(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_print_update_status", lambda: print("status"))
    assert cli._handle_repl_command(":h") is True
    assert cli._handle_repl_command(":examples") is True
    assert cli._handle_repl_command(":ode") is True
    assert cli._handle_repl_command(":tutorial") is True
    assert cli._handle_repl_command(":tour") is True
    assert cli._handle_repl_command(":version") is True
    assert cli._handle_repl_command(":check") is True
    assert cli._handle_repl_command(":wat") is True
    assert cli._handle_repl_command("2+2") is False
    captured = capsys.readouterr()
    err = captured.err
    out = captured.out
    assert "guided tour:" in out
    assert "ode quick reference:" in out
    assert "unknown command" in err


def test_tutorial_command_flow(capsys):
    state = {"active": False, "index": 0}
    assert cli._tutorial_command(":next", state) is True
    err = capsys.readouterr().err
    assert "start with :tutorial" in err
    assert cli._tutorial_command(":tutorial", state) is True
    out = capsys.readouterr().out
    assert "tutorial mode started" in out
    assert "step 1/6" in out
    assert cli._tutorial_command(":next", state) is True
    out = capsys.readouterr().out
    assert "step 2/6" in out
    assert cli._tutorial_command(":repeat", state) is True
    out = capsys.readouterr().out
    assert "step 2/6" in out
    assert cli._tutorial_command(":done", state) is True
    out = capsys.readouterr().out
    assert "tutorial mode ended" in out


def test_try_parse_repl_inline_options():
    parsed = cli._try_parse_repl_inline_options("--latex 2+2")
    assert parsed is not None
    assert parsed[0] == "latex"
    assert parsed[-1] == ["2+2"]

    parsed = cli._try_parse_repl_inline_options("phil --latex 2+2")
    assert parsed is not None
    assert parsed[0] == "latex"
    assert parsed[-1] == ["2+2"]

    assert cli._try_parse_repl_inline_options("2+2") is None


def test_eq_has_top_level_comma():
    assert cli._eq_has_top_level_comma("Eq(x, y)") is True
    assert cli._eq_has_top_level_comma("Eq(d(y(x), x), y(x))") is True
    assert cli._eq_has_top_level_comma("Eq(d(y(x), x) y(x))") is False


def test_main_module_executes():
    with pytest.raises(SystemExit):
        runpy.run_module("calc.__main__", run_name="__main__")


def test_cli_module_main_executes():
    with pytest.raises(SystemExit):
        runpy.run_module("calc.cli", run_name="__main__")
