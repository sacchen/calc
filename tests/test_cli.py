import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "calc", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_success_exit_code():
    proc = run_cli("2+2")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "4"
    assert "try WolframAlpha" not in proc.stderr


def test_cli_invalid_expression_exit_code():
    proc = run_cli("bad(")
    assert proc.returncode == 1
    assert "E:" in proc.stderr
    assert "hint:" in proc.stderr
    assert "hint: try WolframAlpha:" in proc.stderr
    assert "wolframalpha.com/input?i=bad%28" in proc.stderr


def test_cli_help_flag():
    proc = run_cli("--help")
    assert proc.returncode == 0
    assert "usage:" in proc.stdout
    assert "phil v" in proc.stdout
    assert ":examples" in proc.stdout


def test_cli_unknown_option_exit_code():
    proc = run_cli("--wat")
    assert proc.returncode == 1
    assert "unknown option" in proc.stderr


def test_cli_bad_derivative_syntax_has_specific_hint():
    proc = run_cli("d(sin(x)/dx")
    assert proc.returncode == 1
    assert "derivative syntax:" in proc.stderr


def test_cli_bad_matrix_syntax_has_specific_hint():
    proc = run_cli("Matrix([1,2],[3,4])")
    assert proc.returncode == 1
    assert "matrix syntax:" in proc.stderr


def test_cli_bad_dsolve_function_notation_has_specific_hint():
    proc = run_cli("dsolve(Eq(d(y, x), y), y)")
    assert proc.returncode == 1
    assert "for ODEs, use function notation" in proc.stderr
    assert "y(x)" in proc.stderr


def test_cli_accepts_prime_notation_ode():
    proc = run_cli("y' = y")
    assert proc.returncode == 0
    assert "Derivative(y(x), x)" in proc.stdout


def test_cli_accepts_latex_leibniz_ode():
    proc = run_cli(r"\frac{dy}{dx} = y")
    assert proc.returncode == 0
    assert "Derivative(y(x), x)" in proc.stdout


def test_cli_relaxed_sinx_shows_interpretation_hint():
    proc = run_cli("sinx")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "sin(x)"
    assert "interpreted 'sinx' as 'sin(x)'" in proc.stderr


def test_cli_explain_parse_shows_normalized_expression():
    proc = run_cli("--explain-parse", "sinx")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "sin(x)"
    assert "hint: parsed as: sin(x)" in proc.stderr


def test_cli_strict_sinx_does_not_autocorrect():
    proc = run_cli("--strict", "sinx")
    assert proc.returncode == 1
    assert "name 'sinx' is not defined" in proc.stderr
    assert "interpreted 'sinx'" not in proc.stderr


def test_cli_examples_shortcut():
    proc = run_cli(":examples")
    assert proc.returncode == 0
    assert "examples:" in proc.stdout


def test_cli_tutorial_shortcut():
    proc = run_cli(":tutorial")
    assert proc.returncode == 0
    assert "guided tour:" in proc.stdout
    assert "full tutorial: TUTORIAL.md" in proc.stdout


def test_cli_ode_shortcut():
    proc = run_cli(":ode")
    assert proc.returncode == 0
    assert "ode quick reference:" in proc.stdout
    assert "dsolve(Eq(d(y(x), x), y(x)), y(x))" in proc.stdout


def test_repl_help_and_quit():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input=":h\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "phil v" in proc.stdout
    assert ":h help" in proc.stdout
    assert "repl commands:" in proc.stdout


def test_repl_tutorial_command():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input=":tutorial\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "tutorial mode started" in proc.stdout
    assert "step 1/6" in proc.stdout


def test_repl_interactive_tutorial_flow():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input=":tutorial\n:next\n:repeat\n:done\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "tutorial mode started" in proc.stdout
    assert "step 1/6" in proc.stdout
    assert "step 2/6" in proc.stdout
    assert "tutorial mode ended" in proc.stdout


def test_repl_ode_command():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input=":ode\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "ode quick reference:" in proc.stdout


def test_repl_unknown_command_hint():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input=":wat\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "unknown command" in proc.stderr
    assert "use :h" in proc.stderr


def test_repl_error_shows_wolframalpha_hint():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input="bad(\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "hint: try WolframAlpha:" in proc.stderr


def test_repl_default_relaxed_accepts_implicit_multiplication():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input="2x\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "2*x" in proc.stdout


def test_repl_relaxed_sinx_shows_interpretation_hint():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input="sinx\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "sin(x)" in proc.stdout
    assert "interpreted 'sinx' as 'sin(x)'" in proc.stderr


def test_repl_inline_explain_parse_shows_normalized_expression():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input="--explain-parse sinx\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "sin(x)" in proc.stdout
    assert "hint: parsed as: sin(x)" in proc.stderr


def test_repl_strict_rejects_implicit_multiplication():
    proc = subprocess.run(
        [sys.executable, "-m", "calc", "--strict"],
        input="2x\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "E:" in proc.stderr
    assert "invalid syntax" in proc.stderr


def test_repl_inline_option_for_latex():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input="--latex d(x^2, x)\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "2 x" in proc.stdout


def test_repl_prefixed_command_style_line():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input='phil --latex "d(x^2, x)"\n:q\n',
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "2 x" in proc.stdout


def test_cli_latex_output():
    proc = run_cli("--latex", "d(x^2, x)")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "2 x"


def test_cli_latex_inline_output():
    proc = run_cli("--latex-inline", "d(x^2, x)")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "$2 x$"


def test_cli_latex_block_output():
    proc = run_cli("--latex-block", "d(x^2, x)")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "$$\n2 x\n$$"


def test_cli_pretty_output():
    proc = run_cli("--format", "pretty", "Matrix([[1,2],[3,4]])")
    assert proc.returncode == 0
    assert "1  2" in proc.stdout
    assert "3  4" in proc.stdout


def test_cli_json_output():
    proc = run_cli("--format", "json", "sinx")
    assert proc.returncode == 0
    assert proc.stdout.strip() == '{"input":"sinx","parsed":"sin(x)","result":"sin(x)"}'


def test_cli_no_simplify():
    proc = run_cli("--no-simplify", "sin(x)^2 + cos(x)^2")
    assert proc.returncode == 0
    assert "sin(x)**2 + cos(x)**2" in proc.stdout


def test_cli_unknown_format_mode():
    proc = run_cli("--format", "wat", "2+2")
    assert proc.returncode == 1
    assert "unknown format mode" in proc.stderr


def test_cli_color_always_styles_diagnostics():
    proc = run_cli("--color=always", "bad(")
    assert proc.returncode == 1
    assert "\x1b[31mE:" in proc.stderr
    assert "\x1b[33mhint:" in proc.stderr


def test_cli_color_never_disables_styles():
    proc = run_cli("--color=never", "bad(")
    assert proc.returncode == 1
    assert "\x1b[31m" not in proc.stderr
    assert "\x1b[33m" not in proc.stderr


def test_cli_relaxed_long_expression():
    proc = run_cli("(854/2197)e^{8t}+(1343/2197)e^{-5t}+((9/26)t^2 -(9/169)t)e^{8t}")
    assert proc.returncode == 0
    assert "exp(" in proc.stdout
    assert "hint: try WolframAlpha:" in proc.stderr


def test_cli_force_wolfram_hint():
    proc = run_cli("--wa", "2+2")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "4"
    assert "hint: try WolframAlpha:" in proc.stderr


def test_cli_version_shortcut():
    proc = run_cli(":version")
    assert proc.returncode == 0
    assert "phil v" in proc.stdout


def test_cli_update_shortcut():
    proc = run_cli(":update")
    assert proc.returncode == 0
    assert "current version:" in proc.stdout
    assert "uv tool upgrade philcalc" in proc.stdout


def test_cli_check_shortcut():
    proc = run_cli(":check")
    assert proc.returncode == 0
    assert "current version:" in proc.stdout
    assert "update with:" in proc.stdout


def test_repl_assignment_and_ans():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input="A = Matrix([[1,2],[3,4]])\ndet(A)\nans+1\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "Matrix([[1, 2], [3, 4]])" in proc.stdout
    assert "phil> -2" in proc.stdout
    assert "phil> -1" in proc.stdout


def test_repl_reserved_name_f_has_specific_hint_without_wa():
    proc = subprocess.run(
        [sys.executable, "-m", "calc"],
        input="ff = x^3 + 2x\nf = x^3 + 2x\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "'f' is reserved for function notation in ODEs; try 'ff'" in proc.stderr
    assert "input?i=f+%3D+x%5E3+%2B+2x" not in proc.stderr


def test_repl_json_format():
    proc = subprocess.run(
        [sys.executable, "-m", "calc", "--format", "json"],
        input="2+2\n:q\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert '{"input":"2+2","parsed":"2+2","result":"4"}' in proc.stdout
