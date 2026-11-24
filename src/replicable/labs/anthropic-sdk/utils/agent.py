from .log import logger


def concatenate_interrupted_responses(session, index):
    """Remove a run of continuations from `session` and return their merged content.

    `index` is the position in `session` of the first truncated assistant message.
    From there the messages strictly alternate: assistant, "continue" user,
    assistant, "continue" user, ..., and the FINAL assistant response (the one that
    ended the run) must already be appended, so it is the last message. Each message's
    `content` must be a list of dicts (see `blocks_to_dicts`).

    All assistant blocks are kept unchanged, in the order the model produced them,
    and the "continue" user messages are dropped. Text blocks are not joined:
    `[text "a"]` then `[text "b", tool_use]` gives `[text "a", text "b", tool_use]`.

    Earlier text can therefore come before a `thinking` block of the final response.
    Check that the API accepts this before turning on extended thinking.

    Mutates `session`: every message from `index` onwards is deleted. Returns the
    merged list of content blocks, for the caller to append back as one assistant
    message: `{"role": ASSISTANT, "content": returned_blocks}`.
    """
    assistants = session[index::2]

    # `assistants` includes the final response, so this is every block once, in order.
    # Adjacent text blocks stay separate; `on_end_turn` joins them for the result.
    final = session[-1]
    final["content"] = [
        block for assistant in assistants for block in assistant["content"]
    ]

    # Remove the whole run; the caller appends the merged message in its place.
    del session[index:]

    logger.debug("    joined responses' fragmented text")
    return final["content"]
