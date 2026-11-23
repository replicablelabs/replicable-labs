# k00 tests

Unit tests for the k00 sandbox.

## Run them

From the lab directory (`src/replicable/labs/anthropic-sdk`):

```bash
cd src/replicable/labs/anthropic-sdk
uv run pytest                     # only k00
uv run pytest -v                  # one line per test
uv run pytest -x                  # stop at the first failure
```

Run one area, one file or one test:

```bash
cd src/replicable/labs/anthropic-sdk
uv run pytest k00/tests/db
uv run pytest k00/tests/tools/test_create_card.py
uv run pytest k00/tests/test_schemas.py::test_every_status_is_exercised_by_a_case
uv run pytest k00 -k "not_found"      # tests whose name or parameters match
```

`pyproject.toml` sets `testpaths = ["k00"]` and `--import-mode=importlib`, so a plain
`pytest` finds every kata's tests and two katas can both have a `test_tools.py`.

## Layout

```
conftest.py               shared fixtures (below)
db/                       the in-memory card store
  test_store.py           seed data, ids, reset, delete
  test_search.py          fuzzy search ranking and scores
tools/                    what each tool returns when the tool runner calls it
  test_create_card.py     created / exists / replaced
  test_delete_card.py
  test_schedule_card.py
  test_read_tools.py      list_cards, get_card, find_card
  test_run_tool.py        the tool runner and the @tool decorator
test_schemas.py           the contract between the tool code and the model
```

`test_schemas.py` sits at the top because it spans every tool. It checks that what the
model is told matches what the code does:

- each tool's name, parameters and required list match its signature and docstring;
- every status a tool returns, and every member of `Status`, is named in a description;
- every argument appears in the description in brackets, e.g. `[title]`;
- every description names the result keys `[status]` and `[cards]`.

## Fixtures (`conftest.py`)

- `fresh_db`: runs automatically before every test and resets the card store to its seed
  data (cards `1`, `2`, `3`), so tests never see each other's changes.
- `call(name, **kwargs)`: runs a tool through `run_tool` and returns `(result, is_error)`.
  On success `result` is the parsed JSON (`{"status": ..., "cards": [...]}`); on an error
  it is the error text.

```python
def test_get_card(call):
    out, err = call("get_card", id="2")
    assert not err and out["cards"][0]["title"] == "Team standup"
```

## Adding to them

- **A new tool:** register it in `tools/__init__.py`, add `tools/test_<tool>.py`, and add
  a case to `STATUS_CASES` in `test_schemas.py` for each status it can return.
  The schema tests cover the new tool automatically.
- **A new status:** add the member to `Status` in `tools/schemas.py`. Two tests fail until it
  has a case in `STATUS_CASES` and is mentioned (in quotes, e.g. `"archived"`) in a tool
  description.
