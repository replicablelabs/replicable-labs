"""`concatenate_interrupted_responses`: gluing an answer that arrived in pieces.

A stitched conversation looks like: prompt, piece, "continue", piece, "continue", last
piece. The function takes everything after the prompt out and returns it as one message.
"""

import pytest

from utils.agent import concatenate_interrupted_responses

TOOL = {"type": "tool_use", "id": "t1", "name": "list_cards", "input": {}}
THINKING = {"type": "thinking", "thinking": "hmm", "signature": "s"}


def txt(value):
    """A text block, as stored in the session."""
    return {"type": "text", "text": value}


def interrupted(*pieces):
    """A session with a prompt, then one assistant message per piece with "continue" between."""
    session = [{"role": "user", "content": "prompt"}]
    for i, blocks in enumerate(pieces):
        if i:
            session.append({"role": "user", "content": "continue"})
        session.append({"role": "assistant", "content": list(blocks)})
    return session


@pytest.mark.parametrize(
    "pieces",
    [
        [[txt("Paris")]],
        [[txt("Pa")], [txt("ris")]],
        [[txt("P")], [txt("a"), txt("r")], [txt("is")]],
    ],
    ids=["one piece", "two pieces", "three pieces"],
)
def test_pieces_become_one_message_in_order(pieces):
    """Every block is kept once, in order, so read together they are the whole answer."""
    merged = concatenate_interrupted_responses(interrupted(*pieces), 1)

    assert merged == [block for piece in pieces for block in piece]
    assert "".join(block["text"] for block in merged) == "Paris"


def test_the_run_is_removed_and_earlier_messages_stay():
    """Pieces and "continue" messages leave the session; what came before is untouched."""
    session = interrupted([txt("Pa")], [txt("ris")])

    concatenate_interrupted_responses(session, 1)

    assert session == [{"role": "user", "content": "prompt"}]


@pytest.mark.parametrize(
    "last",
    [[], [TOOL], [txt("b"), TOOL], [THINKING, txt("b"), TOOL]],
    ids=["empty", "tool", "text and tool", "thinking, text and tool"],
)
def test_the_last_piece_keeps_its_blocks_and_order(last):
    """What the model ended on follows the earlier text, with nothing lost or moved.

    In particular the text stays in front of the tool call, as the model wrote it.
    """
    merged = concatenate_interrupted_responses(interrupted([txt("a")], last), 1)

    assert merged == [txt("a"), *last]
