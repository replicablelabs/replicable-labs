"""Small helpers: printing, block conversion, prompt files and the `max_tokens` cap."""

from pathlib import Path

import pytest

from utils import utils

PROMPTS = Path(utils.__file__).parent.parent / "prompts"


@pytest.mark.parametrize("keep_none", [False, True])
def test_show_hides_empty_fields_unless_asked(capsys, text, message, keep_none):
    """Printing a response skips its empty fields, which are mostly noise, by default."""
    utils.show(message("end_turn", text("Hello")), keep_none=keep_none)

    out = capsys.readouterr().out
    assert "Hello" in out
    assert ("stop_sequence" in out) is keep_none


def test_blocks_to_dicts_handles_sdk_blocks_and_dicts(text):
    """SDK objects become plain dicts without empty fields; dicts pass straight through."""
    ready = {"type": "text", "text": "b", "citations": None}
    blocks = [text("a"), ready]

    out = utils.blocks_to_dicts(blocks)

    assert out == [{"type": "text", "text": "a"}, ready]
    assert out[1] is ready
    assert out is not blocks


@pytest.mark.parametrize(
    "read,filename",
    [
        (utils.get_system_prompt, "system.md"),
        (utils.get_max_tokens_cutover_prompt, "max_tokens_merge.md"),
    ],
)
def test_prompts_come_from_their_file_trimmed(read, filename):
    """Each prompt is its own file's text, with no stray blank lines around it."""
    prompt = read()
    assert prompt and prompt == (PROMPTS / filename).read_text(encoding="utf-8").strip()


def test_reset_returns_the_starting_cap():
    """Resetting means going back to where a fresh run starts."""
    assert utils.reset_max_tokens_cap() == utils.set_max_tokens_cap() > 0


@pytest.mark.parametrize(
    "cap,bigger",
    [
        (100, 200),
        (utils.MAX_TOKENS_CEILING // 2, utils.MAX_TOKENS_CEILING),
        (utils.MAX_TOKENS_CEILING - 1, utils.MAX_TOKENS_CEILING),
        (utils.MAX_TOKENS_CEILING, utils.MAX_TOKENS_CEILING),
    ],
)
def test_increase_doubles_up_to_the_ceiling(cap, bigger):
    """The cap doubles, but never past what the model can output."""
    assert utils.increase_max_tokens_cap(cap) == bigger
