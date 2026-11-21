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
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> str:
        result = func(*args, **kwargs)
        assert isinstance(result, BaseModel), f"{func.__name__} must return a result model"
        return result.model_dump_json(exclude_none=True)

    return beta_tool(wrapper)
