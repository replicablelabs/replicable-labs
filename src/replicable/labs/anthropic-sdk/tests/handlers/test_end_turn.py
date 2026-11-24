"""`on_end_turn`: the model is done, so its text becomes the answer and the loop stops."""

from handlers.end_turn import on_end_turn
from state import AgentState


def test_text_becomes_the_result_and_the_loop_stops(text, message):
    """The response is saved in the conversation and its text is the final answer."""
    state = AgentState.start("hi")

    assert on_end_turn(state, message("end_turn", text("Hello"))) is True

    assert state.result == "Hello"
    assert state.session[-1] == {
        "role": "assistant", "content": [{"type": "text", "text": "Hello"}],
    }


def test_only_text_reaches_the_user(text, thinking, message):
    """Text blocks are joined; the model's private thinking is stored but not shown."""
    state = AgentState.start("hi")

    on_end_turn(state, message("end_turn", thinking("hmm"), text("Pa"), text("ris")))

    assert state.result == "Paris"
    assert [b["type"] for b in state.session[-1]["content"]] == ["thinking", "text", "text"]


def test_an_answer_without_text_is_empty(message):
    """A response with no content is an empty answer, not a crash."""
    state = AgentState.start("hi")

    assert on_end_turn(state, message("end_turn")) is True

    assert state.result == ""


def test_open_continue_run_is_stitched_into_the_answer(text, message):
    """When an answer arrived in pieces, the user gets the whole of it, not the last piece."""
    state = AgentState.start("hi", cutover_index=1)
    state.session.append({"role": "assistant", "content": [{"type": "text", "text": "Par"}]})
    state.append_user("continue")

    on_end_turn(state, message("end_turn", text("is")))

    assert state.result == "Paris"
    assert [m["role"] for m in state.session] == ["user", "assistant"]
    assert state.cutover_index is None
