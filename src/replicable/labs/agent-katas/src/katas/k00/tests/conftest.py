"""Shared fixtures for the k00 tests."""

import json

import pytest

from katas.k00 import db
from katas.k00.tools import run_tool


@pytest.fixture(autouse=True)
def fresh_db():
    """Reset the card store to its seed data before every test."""
    db.reset()


@pytest.fixture
def call():
    """Call a tool by name; returns (parsed result or error text, is_error)."""

    def _call(name, **kwargs):
        """Run the tool `name` with `kwargs` as its input."""
        content, is_error = run_tool(name, kwargs)
        return (content if is_error else json.loads(content)), is_error

    return _call
