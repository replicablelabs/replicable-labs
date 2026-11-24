"""The `kata` command: from shell words to a call to the agent, without calling the API."""

import runpy
from unittest.mock import Mock

import pytest

import agent
import cli
import tracing


@pytest.fixture(autouse=True)
def runs(monkeypatch):
    """Replace the agent, the client and the trace flush; returns the mocked parts."""
    monkeypatch.setenv("NO_COLOR", "1")
    mocks = Mock()
    monkeypatch.setattr(agent, "main", mocks.main)
    monkeypatch.setattr(tracing, "flush", mocks.flush)
    monkeypatch.setattr("anthropic.Anthropic", mocks.Anthropic)
    return mocks


@pytest.mark.parametrize(
    "argv,prompt",
    [
        (["run", "list", "my", "cards"], "list my cards"),
        (["run", "list my cards"], "list my cards"),
        (["run"], cli.DEFAULT_PROMPT),
    ],
    ids=["words", "quoted", "no prompt"],
)
def test_run_passes_the_prompt_to_the_agent(runs, capsys, argv, prompt):
    """Quotes are optional, and with no prompt a default one is sent."""
    cli.main(argv)
    runs.main.assert_called_once_with(runs.Anthropic.return_value, prompt)
    assert "[running agent.py]" in capsys.readouterr().out


def test_traces_are_flushed_after_the_run(runs):
    """Traces go out in the background, so the command waits for them after the run."""
    cli.main(["run", "hi"])
    assert [c[0] for c in runs.mock_calls] == ["Anthropic", "main", "flush"]


def test_traces_are_flushed_even_when_the_agent_crashes(runs):
    """A crash is when the trace matters most; it is sent and the error still surfaces."""
    runs.main.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError, match="boom"):
        cli.main(["run", "hi"])
    runs.flush.assert_called_once_with()


def test_missing_agent_main_is_explained(monkeypatch, capsys):
    """Breaking agent.py while editing gives a clear message, not an AttributeError."""
    monkeypatch.delattr(agent, "main")
    with pytest.raises(SystemExit) as exit_:
        cli.main(["run"])
    assert exit_.value.code == 1
    assert "agent.py needs a `main(client, prompt)`" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [[], ["nope"]])
def test_bad_commands_show_usage(runs, capsys, argv):
    """A missing or unknown subcommand prints help and never starts the agent."""
    with pytest.raises(SystemExit) as exit_:
        cli.main(argv)
    assert exit_.value.code == 2
    assert "usage: kata" in capsys.readouterr().err
    runs.main.assert_not_called()


@pytest.mark.parametrize("configured", [None, "ANTHROPIC_API_KEY", "ANTHROPIC_PROFILE"])
def test_client_warns_only_without_credentials(monkeypatch, runs, capsys, configured):
    """Either way of signing in is enough; with neither, a hint appears on stderr."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_PROFILE", raising=False)
    if configured:
        monkeypatch.setenv(configured, "test-value")

    assert cli._client() is runs.Anthropic.return_value

    assert ("is set" in capsys.readouterr().err) is (configured is None)


def test_running_the_file_loads_env_and_starts_the_command(monkeypatch, runs):
    """`python cli.py run hi` works, and the shell's variables win over the `.env` file."""
    load = Mock()
    monkeypatch.setattr("dotenv.load_dotenv", load)
    monkeypatch.setattr("sys.argv", ["kata", "run", "hi"])

    runpy.run_path(cli.__file__, run_name="__main__")

    (path,), options = load.call_args
    assert path.name == ".env" and options == {"override": False}
    runs.main.assert_called_once_with(runs.Anthropic.return_value, "hi")
