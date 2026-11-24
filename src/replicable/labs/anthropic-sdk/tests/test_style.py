"""Terminal colours: on for a person at a terminal, off for pipes and files."""

import io
import sys

import pytest

import style


class Terminal(io.StringIO):
    """A stream that claims to be a terminal."""

    def isatty(self):
        return True


@pytest.fixture(autouse=True)
def no_color_env(monkeypatch):
    """Start without the colour variables, whatever the shell exports."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)


@pytest.mark.parametrize(
    "env,stream,colour",
    [
        ({}, Terminal(), True),
        ({}, io.StringIO(), False),
        ({"FORCE_COLOR": "1"}, io.StringIO(), True),
        ({"NO_COLOR": "1"}, Terminal(), False),
        ({"NO_COLOR": "1", "FORCE_COLOR": "1"}, Terminal(), False),
    ],
    ids=["terminal", "pipe", "forced", "disabled", "disabled wins"],
)
def test_when_text_is_coloured(monkeypatch, env, stream, colour):
    """Terminals get colour and pipes do not; the variables override, NO_COLOR above all."""
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    assert style.red("x", stream) == ("\033[31;1mx\033[0m" if colour else "x")


@pytest.mark.parametrize(
    "paint,code",
    [
        (style.red, "31;1"),
        (style.green, "32"),
        (style.yellow, "33"),
        (style.cyan, "36"),
        (style.dim, "2"),
        (style.bold, "1"),
    ],
)
def test_each_helper_uses_its_code_and_resets(monkeypatch, paint, code):
    """Each helper has its own colour and switches it off after the text (default: stdout)."""
    monkeypatch.setattr(sys, "stdout", Terminal())
    assert paint("x") == f"\033[{code}mx\033[0m"


def test_die_reports_on_stderr_and_exits_with_failure(capsys):
    """Scripts see a failing exit code, and stdout stays clean."""
    with pytest.raises(SystemExit) as exit_:
        style.die("boom")
    assert exit_.value.code == 1
    out = capsys.readouterr()
    assert (out.out, out.err) == ("", "boom\n")


@pytest.mark.parametrize("stream,installs", [(Terminal(), True), (io.StringIO(), False)])
def test_pretty_tracebacks_only_on_a_terminal(monkeypatch, stream, installs):
    """Tracebacks are coloured for a person and left plain in a log file."""
    calls = []
    monkeypatch.setattr("rich.traceback.install", lambda **kw: calls.append(kw))
    monkeypatch.setattr(sys, "stderr", stream)

    style.pretty_tracebacks()

    assert bool(calls) is installs


def test_pretty_tracebacks_are_optional(monkeypatch):
    """Without `rich` the program still runs, with ordinary tracebacks."""
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setitem(sys.modules, "rich.traceback", None)  # makes the import fail
    style.pretty_tracebacks()
