"""`@tool`: `@beta_tool` for functions that return a result model.

`@beta_tool` needs a function that returns a string, so this wrapper serialises
the returned pydantic model (unset fields dropped) and then applies `@beta_tool`.
The name, description and input schema still come from the original function's
signature and docstring.
"""

import functools

from anthropic import beta_tool
from pydantic import BaseModel


def tool(func):
    """Turn `func` (which returns a result model) into a `@beta_tool`."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> str:
        """Call `func` and return its result model as JSON (`functools.wraps` replaces this
        docstring with `func`'s, which is what the model sees as the tool description)."""
        result = func(*args, **kwargs)
        assert isinstance(result, BaseModel), f"{func.__name__} must return a result model"
        return result.model_dump_json(exclude_none=True)

    return beta_tool(wrapper)
