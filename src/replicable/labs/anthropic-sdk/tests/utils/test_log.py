"""Debug logging: silent unless `DEBUG` asks for it, and never on stdout."""

import importlib
import logging
import sys

import pytest

from utils import log


@pytest.fixture
def reload_log():
    """Re-run the module's setup code, then put the shared logger back as it was."""
    level, handlers = log.logger.level, list(log.logger.handlers)
    yield lambda: importlib.reload(log)
    log.logger.setLevel(level)
    log.logger.handlers[:] = handlers


@pytest.mark.parametrize("value", ["1", "true", "YES", " On "])
def test_truthy_values_turn_debug_on(monkeypatch, value):
    """Any usual way of saying yes works, whatever its case or surrounding spaces."""
    monkeypatch.setenv("DEBUG", value)
    assert log.debug_enabled() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "maybe"])
def test_other_values_leave_debug_off(monkeypatch, value):
    """`DEBUG=0` really means off: being set is not enough."""
    monkeypatch.setenv("DEBUG", value)
    assert log.debug_enabled() is False


def test_debug_is_off_when_unset(monkeypatch):
    """With no configuration the agent is quiet."""
    monkeypatch.delenv("DEBUG", raising=False)
    assert log.debug_enabled() is False


@pytest.mark.parametrize("value,level", [("1", logging.DEBUG), ("0", logging.WARNING)])
def test_debug_decides_the_level_at_import(monkeypatch, reload_log, value, level):
    """Debug lines show only with `DEBUG`; warnings and errors always show."""
    monkeypatch.setenv("DEBUG", value)
    reload_log()
    assert log.logger.level == level


def test_first_import_logs_to_stderr_without_propagating(reload_log):
    """Logs stay off stdout and are not repeated by the root logger."""
    log.logger.handlers.clear()

    reload_log()

    (handler,) = log.logger.handlers
    assert handler.stream is sys.stderr
    assert log.logger.propagate is False


def test_importing_again_adds_no_second_handler(reload_log):
    """A second handler would print every line twice."""
    before = list(log.logger.handlers)
    assert before
    reload_log()
    assert log.logger.handlers == before
