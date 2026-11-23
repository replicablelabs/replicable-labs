"""Shared fixtures for the tests."""

import json

import pytest

import db
from tools import run_tool


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
