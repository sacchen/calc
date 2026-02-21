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
    opts = cli._parse_options(["--latex", "--strict", "--explain-parse", "--wa", "--copy-wa", "2+2"])
    assert opts.format_mode == "latex"
    assert opts.relaxed is False
    assert opts.simplify_output is True
    assert opts.explain_parse is True
    assert opts.always_wa is True
    assert opts.copy_wa is True
    assert opts.color_mode == "auto"
    assert opts.remaining == ("2+2",)


def test_parse_options_latex_modes():
    assert cli._parse_options(["--latex-inline", "x"]).format_mode == "latex-inline"
    assert cli._parse_options(["--latex-block", "x"]).format_mode == "latex-block"


def test_parse_options_format_and_no_simplify():
    opts = cli._parse_options(["--format", "pretty", "--no-simplify", "2+2"])
    assert opts.format_mode == "pretty"
    assert opts.simplify_output is False
    assert opts.remaining == ("2+2",)


def test_parse_options_json_format():
    assert cli._parse_options(["--format", "json", "x"]).format_mode == "json"
    assert cli._parse_options(["--format=json", "x"]).format_mode == "json"


def test_parse_options_format_errors():
    with pytest.raises(ValueError, match="missing value for --format"):
        cli._parse_options(["--format"])
    with pytest.raises(ValueError, match="unknown format mode"):
        cli._parse_options(["--format=wat", "x"])


def test_parse_options_double_dash_and_single_dash_literal():
    assert cli._parse_options(["--", "--not-an-option"]).remaining == ("--not-an-option",)
    assert cli._parse_options(["-1"]).remaining == ("-1",)


def test_parse_options_color_modes():
    opts = cli._parse_options(["--color", "always", "2+2"])
    assert opts.color_mode == "always"
    assert opts.remaining == ("2+2",)
    opts = cli._parse_options(["--color=never", "2+2"])
    assert opts.color_mode == "never"
    assert opts.remaining == ("2+2",)


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
    assert "linalg syntax" in cli._hint_for_error("unknown linalg subcommand")
    assert "reserved for function notation" in cli._hint_for_error("cannot assign reserved name: f")
    assert "reserved by phil internals" in cli._hint_for_error("cannot assign reserved name: sin")
    assert cli._hint_for_error("different error") is None


def test_is_complex_expression_heuristics():
    assert cli._is_complex_expression("x" * 40) is True
    assert cli._is_complex_expression("d(x^2, x)") is True
    assert cli._is_complex_expression("2+2") is False


def test_should_use_color_invalid_mode(monkeypatch):
    monkeypatch.setattr(cli.sys.stderr, "isatty", lambda: True)
    assert cli._should_use_color(cli.sys.stderr, "invalid") is False


def test_format_result_latex():
    assert cli._format_result("x", format_mode="plain") == "x"
    assert cli._format_result(2, format_mode="latex") == "2"
    assert cli._format_result(2, format_mode="latex-inline") == "$2$"
    assert cli._format_result(2, format_mode="latex-block") == "$$\n2\n$$"


def test_format_json_result():
    out = cli._format_json_result("sinx", relaxed=True, value="sin(x)")
    assert out == '{"input":"sinx","parsed":"sin(x)","result":"sin(x)"}'


def test_split_top_level_commas_for_ode_inputs():
    assert cli._split_top_level_commas("y' = y, y(0)=1") == ["y' = y", "y(0)=1"]
    assert cli._split_top_level_commas("y' = x*y, y(0)=1, y(1)=2") == ["y' = x*y", "y(0)=1", "y(1)=2"]


def test_infer_ode_dependent_wrapper():
    eq_value = cli.evaluate("Eq(d(y(x), x), y(x))")
    dep = cli._infer_ode_dependent(eq_value)
    assert str(dep) == "y(x)"


def test_evaluate_ode_alias_success():
    value, parsed = cli._evaluate_ode_alias("ode y' = y", relaxed=True, simplify_output=True, session_locals={})
    assert "Eq(y(x), C1*exp(x))" in str(value)
    assert parsed.startswith("dsolve(Eq(")


def test_evaluate_ode_alias_with_ics():
    value, parsed = cli._evaluate_ode_alias("ode y' = y, y(0)=1", relaxed=True, simplify_output=True, session_locals={})
    assert str(value) == "Eq(y(x), exp(x))"
    assert "ics={y(0): 1}" in parsed


def test_evaluate_ode_alias_errors():
    with pytest.raises(ValueError, match="ode expects an equation"):
        cli._evaluate_ode_alias("ode ", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="ode expects an equation"):
        cli._evaluate_ode_alias("ode x+1", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="could not infer dependent function"):
        cli._evaluate_ode_alias("ode Eq(x, 1)", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="initial condition must be an equation"):
        cli._evaluate_ode_alias("ode y' = y, 1", relaxed=True, simplify_output=True, session_locals={})


def test_evaluate_linalg_alias_solve_success():
    value, parsed = cli._evaluate_linalg_alias(
        "linalg solve A=[[2,1],[1,3]] b=[1,2]",
        relaxed=True,
        simplify_output=True,
        session_locals={},
    )
    assert str(value) == "Matrix([[1/5], [3/5]])"
    assert parsed == "msolve(Matrix([[2,1],[1,3]]), Matrix([1,2]))"


def test_evaluate_linalg_alias_rref_success():
    value, parsed = cli._evaluate_linalg_alias(
        "linalg rref A=[[1,2],[2,4]]",
        relaxed=True,
        simplify_output=True,
        session_locals={},
    )
    assert str(value).endswith(", (0,))")
    assert parsed == "rref(Matrix([[1,2],[2,4]]))"


def test_evaluate_linalg_alias_errors():
    with pytest.raises(ValueError, match="expects a subcommand"):
        cli._evaluate_linalg_alias("linalg ", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="unknown linalg subcommand"):
        cli._evaluate_linalg_alias("linalg wat A=[[1]]", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="missing linalg parameter"):
        cli._evaluate_linalg_alias("linalg solve A=[[1]]", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="square A"):
        cli._evaluate_linalg_alias("linalg solve A=[[1,2,3],[4,5,6]] b=[1,2]", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="column vector"):
        cli._evaluate_linalg_alias("linalg solve A=[[1,0],[0,1]] b=[[1,2]]", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="len\\(b\\)"):
        cli._evaluate_linalg_alias("linalg solve A=[[1,0],[0,1]] b=[1,2,3]", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="unknown linalg parameter"):
        cli._evaluate_linalg_alias("linalg solve C=[[1,0],[0,1]] b=[1,2]", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="duplicate linalg parameter"):
        cli._evaluate_linalg_alias("linalg solve A=[[1,0],[0,1]] A=[[1,0],[0,1]] b=[1,2]", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="must use '='"):
        cli._evaluate_linalg_alias("linalg solve A [[1,0],[0,1]] b=[1,2]", relaxed=True, simplify_output=True, session_locals={})
    with pytest.raises(ValueError, match="unclosed bracket literal"):
        cli._evaluate_linalg_alias("linalg solve A=[[1,0],[0,1] b=[1,2]", relaxed=True, simplify_output=True, session_locals={})


def test_evaluate_linalg_alias_rref_rejects_non_matrix(monkeypatch):
    monkeypatch.setattr(cli, "evaluate", lambda *a, **k: 123)
    with pytest.raises(ValueError, match="matrix literal for A"):
        cli._evaluate_linalg_alias("linalg rref A=[[1,2],[3,4]]", relaxed=True, simplify_output=True, session_locals={})


def test_evaluate_linalg_alias_solve_rejects_non_matrix_rhs(monkeypatch):
    matrix_ok = cli.evaluate("Matrix([[1,0],[0,1]])")
    calls = {"count": 0}

    def fake_eval(*args, **kwargs):
        calls["count"] += 1
        return matrix_ok if calls["count"] == 1 else 7

    monkeypatch.setattr(cli, "evaluate", fake_eval)
    with pytest.raises(ValueError, match="matrix literals for A and b"):
        cli._evaluate_linalg_alias("linalg solve A=[[1,0],[0,1]] b=[1,2]", relaxed=True, simplify_output=True, session_locals={})


def test_execute_expression_ode_alias_plain_and_json(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_print_wolfram_hint", lambda *a, **k: None)
    cli._execute_expression(
        "ode y' = y",
        format_mode="plain",
        relaxed=True,
        simplify_output=True,
        explain_parse=False,
        always_wa=False,
        copy_wa=False,
        color_mode="never",
        session_locals={},
    )
    out = capsys.readouterr().out
    assert "y(x) = C1*exp(x)" in out

    cli._execute_expression(
        "ode y' = y",
        format_mode="json",
        relaxed=True,
        simplify_output=True,
        explain_parse=True,
        always_wa=False,
        copy_wa=False,
        color_mode="never",
        session_locals={},
    )
    captured = capsys.readouterr()
    assert '"parsed":"dsolve(' in captured.out
    assert "hint: parsed as: dsolve(" in captured.err


def test_execute_expression_linalg_alias_json(capsys):
    cli._execute_expression(
        "linalg solve A=[[2,1],[1,3]] b=[1,2]",
        format_mode="json",
        relaxed=True,
        simplify_output=True,
        explain_parse=True,
        always_wa=False,
        copy_wa=False,
        color_mode="never",
        session_locals={},
    )
    captured = capsys.readouterr()
    assert '"parsed":"msolve(Matrix([[2,1],[1,3]]), Matrix([1,2]))"' in captured.out
    assert "hint: parsed as: msolve(Matrix([[2,1],[1,3]]), Matrix([1,2]))" in captured.err


def test_format_result_pretty():
    from sympy import Matrix

    out = cli._format_result(Matrix([[1, 2], [3, 4]]), format_mode="pretty")
    assert "1  2" in out


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


def test_style_unknown_color_and_dumb_term(monkeypatch):
    monkeypatch.setattr(cli.sys.stderr, "isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    out = cli._style("text", color="red", stream=cli.sys.stderr, color_mode="auto")
    assert out == "text"
    monkeypatch.setenv("TERM", "xterm-256color")
    out = cli._style("text", color="unknown", stream=cli.sys.stderr, color_mode="always")
    assert out == "text"


def test_print_relaxed_rewrite_hints_emits_message(capsys):
    cli._print_relaxed_rewrite_hints("sinx", relaxed=True, color_mode="never")
    err = capsys.readouterr().err
    assert "interpreted 'sinx' as 'sin(x)'" in err


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
    assert "no update needed" in out
    assert "update with:" not in out


def test_print_update_status_update_available(monkeypatch, capsys):
    monkeypatch.setattr(cli, "VERSION", "1.2.3")
    monkeypatch.setattr(cli, "_latest_pypi_version", lambda: "2.0.0")
    cli._print_update_status()
    out = capsys.readouterr().out
    assert "update available" in out
    assert "update with:" in out


def test_print_update_status_latest_unavailable(monkeypatch, capsys):
    monkeypatch.setattr(cli, "VERSION", "1.2.3")
    monkeypatch.setattr(cli, "_latest_pypi_version", lambda: None)
    cli._print_update_status()
    out = capsys.readouterr().out
    assert "unavailable" in out
    assert "retry :check" in out
    assert "update with:" not in out


def test_print_update_status_local_prerelease_newer_than_latest(monkeypatch, capsys):
    monkeypatch.setattr(cli, "VERSION", "0.1.12.dev0")
    monkeypatch.setattr(cli, "_latest_pypi_version", lambda: "0.1.10")
    cli._print_update_status()
    out = capsys.readouterr().out
    assert "newer local/pre-release build" in out
    assert "no update needed" in out
    assert "update available" not in out
    assert "update with:" not in out


def test_print_repl_startup_update_status_non_interactive(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    monkeypatch.setattr(cli, "_latest_pypi_version", lambda: "9.9.9")
    cli._print_repl_startup_update_status()
    out = capsys.readouterr().out
    assert out == ""


def test_print_repl_startup_update_status_up_to_date(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(cli, "VERSION", "1.2.3")
    monkeypatch.setattr(cli, "_latest_pypi_version", lambda: "1.2.3")
    cli._print_repl_startup_update_status()
    out = capsys.readouterr().out
    assert "up to date" in out


def test_print_repl_startup_update_status_update_available(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(cli, "VERSION", "1.2.3")
    monkeypatch.setattr(cli, "_latest_pypi_version", lambda: "2.0.0")
    cli._print_repl_startup_update_status()
    out = capsys.readouterr().out
    assert "available" in out
    assert "update with:" in out


def test_print_repl_startup_update_status_local_prerelease_newer(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(cli, "VERSION", "0.1.12.dev0")
    monkeypatch.setattr(cli, "_latest_pypi_version", lambda: "0.1.10")
    cli._print_repl_startup_update_status()
    out = capsys.readouterr().out
    assert "is newer than latest release" in out
    assert "update with:" not in out


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
    assert cli.run(["?"]) == 0
    assert cli.run(["??"]) == 0
    assert cli.run(["???"]) == 0
    assert cli.run([":examples"]) == 0
    assert cli.run([":tutorial"]) == 0
    assert cli.run([":ode"]) == 0
    assert cli.run([":linalg"]) == 0
    assert cli.run([":la"]) == 0
    assert cli.run([":version"]) == 0
    assert cli.run([":update"]) == 0
    out = capsys.readouterr().out
    assert "help chain:" in out
    assert "power-user shortcuts:" in out
    assert "capability demos:" in out
    assert "10^100000 + 1 - 10^100000" in out
    assert "examples:" in out
    assert "guided tour:" in out
    assert "ode quick reference:" in out
    assert "linear algebra quick reference:" in out
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


def test_run_repl_prints_startup_update_status(monkeypatch, capsys):
    inputs = iter([":q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(cli, "_print_repl_startup_update_status", lambda: print("startup-status"))
    rc = cli.run([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "startup-status" in out


def test_run_repl_does_not_print_always_on_update_line(monkeypatch, capsys):
    inputs = iter([":q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(cli, "_print_repl_startup_update_status", lambda: None)
    rc = cli.run([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "update: uv tool upgrade philcalc" not in out


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
    assert cli._handle_repl_command("?") is True
    assert cli._handle_repl_command("??") is True
    assert cli._handle_repl_command("???") is True
    assert cli._handle_repl_command(":examples") is True
    assert cli._handle_repl_command(":ode") is True
    assert cli._handle_repl_command(":linalg") is True
    assert cli._handle_repl_command(":la") is True
    assert cli._handle_repl_command(":tutorial") is True
    assert cli._handle_repl_command(":tour") is True
    assert cli._handle_repl_command(":version") is True
    assert cli._handle_repl_command(":check") is True
    assert cli._handle_repl_command(":wat") is True
    assert cli._handle_repl_command("2+2") is False
    captured = capsys.readouterr()
    err = captured.err
    out = captured.out
    assert "help chain:" in out
    assert "power-user shortcuts:" in out
    assert "capability demos:" in out
    assert "guided tour:" in out
    assert "ode quick reference:" in out
    assert "linear algebra quick reference:" in out
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


def test_tutorial_command_additional_branches(capsys):
    assert cli._tutorial_command(":done", None) is False
    state = {"active": False, "index": 0}
    assert cli._tutorial_command(":repeat", state) is True
    assert "start with :tutorial" in capsys.readouterr().err
    assert cli._tutorial_command(":done", state) is True
    assert "tutorial is not active" in capsys.readouterr().err
    assert cli._tutorial_command(":tutorial", state) is True
    capsys.readouterr()
    for _ in range(len(cli.TUTORIAL_STEPS)):
        assert cli._tutorial_command(":next", state) is True
    out = capsys.readouterr().out
    assert "tutorial complete. use :done to exit tutorial mode" in out


def test_consume_bracket_literal_invalid_start():
    with pytest.raises(ValueError, match="expected bracketed literal"):
        cli._consume_bracket_literal("A=[[1,2]]", 0)


def test_parse_linalg_keyed_literals_space_only_text():
    assert cli._parse_linalg_keyed_literals("   ", set()) == {}


def test_parse_linalg_keyed_literals_allows_space_after_equals():
    parsed = cli._parse_linalg_keyed_literals("A=   [[1,2],[3,4]]", {"A"})
    assert parsed == {"A": "[[1,2],[3,4]]"}


def test_try_parse_repl_inline_options():
    parsed = cli._try_parse_repl_inline_options("--latex 2+2")
    assert parsed is not None
    assert parsed.format_mode == "latex"
    assert parsed.remaining == ("2+2",)

    parsed = cli._try_parse_repl_inline_options("phil --latex 2+2")
    assert parsed is not None
    assert parsed.format_mode == "latex"
    assert parsed.remaining == ("2+2",)

    assert cli._try_parse_repl_inline_options("2+2") is None


def test_try_parse_repl_inline_options_invalid_shell_input():
    with pytest.raises(ValueError, match="invalid REPL option input"):
        cli._try_parse_repl_inline_options('phil --format "latex')


def test_run_repl_tutorial_command_short_circuits_expression_execution(monkeypatch, capsys):
    inputs = iter([":tutorial", ":q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(cli, "_print_repl_startup_update_status", lambda: None)
    executed: list[str] = []
    monkeypatch.setattr(cli, "_execute_expression", lambda expr, **kwargs: executed.append(expr))
    rc = cli.run([])
    captured = capsys.readouterr()
    assert rc == 0
    assert executed == []
    assert "tutorial mode started" in captured.out


def test_run_repl_inline_options_update_session_settings_only(monkeypatch, capsys):
    inputs = iter(["--latex", ":q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(cli, "_print_repl_startup_update_status", lambda: None)
    executed: list[str] = []
    monkeypatch.setattr(cli, "_execute_expression", lambda expr, **kwargs: executed.append(expr))
    rc = cli.run([])
    captured = capsys.readouterr()
    assert rc == 0
    assert executed == []
    assert "REPL options updated for this session" in captured.err


def test_run_repl_inline_options_with_remaining_expression(monkeypatch, capsys):
    inputs = iter(["--strict 2x", ":q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(cli, "_print_repl_startup_update_status", lambda: None)
    calls: list[tuple[str, bool]] = []

    def fake_execute(expr: str, **kwargs):
        calls.append((expr, kwargs["relaxed"]))

    monkeypatch.setattr(cli, "_execute_expression", fake_execute)
    rc = cli.run([])
    capsys.readouterr()
    assert rc == 0
    assert calls == [("2x", False)]


def test_main_module_executes():
    with pytest.raises(SystemExit):
        runpy.run_module("calc.__main__", run_name="__main__")


def test_cli_module_main_executes():
    with pytest.raises(SystemExit):
        runpy.run_module("calc.cli", run_name="__main__")
