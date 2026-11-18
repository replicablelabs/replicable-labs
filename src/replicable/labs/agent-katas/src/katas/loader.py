"""Tests/live runner pick which implementation of a kata to use: KATA_IMPL=starter (default, buggy) or solution."""
import importlib, os

def load(kata: str, impl: str | None = None):
    return importlib.import_module(f"katas.{kata}.{impl or os.environ.get('KATA_IMPL', 'starter')}")
