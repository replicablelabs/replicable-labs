from .log import logger


def concatenate_interrupted_responses(session, index):
    """Remove a run of continuations from `session` and return their merged content.

    `index` is the position in `session` of the first truncated assistant message.
    From there the messages strictly alternate: assistant, "continue" user,
    assistant, "continue" user, ..., and the FINAL assistant response (the one that
    ended the run) must already be appended, so it is the last message.

    Every block must already be a dict (see `blocks_to_dicts`). The earlier
    assistant messages are text-only (their `tool_use` blocks were stripped). Their
    text is concatenated, with no separator, onto the first text block of the final
    response; any other blocks of the final response (e.g. a `tool_use`) are kept
    in order. The "continue" user messages are dropped.

    Mutates `session`: every message from `index` onwards is deleted. Returns the
    merged list of content blocks, for the caller to append back as one assistant
    message: `{"role": ASSISTANT, "content": returned_blocks}`.
    """
    assistants = session[index::2]
    earlier, final = assistants[:-1], assistants[-1]

    prefix = "".join(
        block["text"]
        for message in earlier
        for block in message["content"]
        if block["type"] == "text"
    )

    blocks = list(final["content"])
    if blocks and blocks[0]["type"] == "text":
        blocks[0] = {**blocks[0], "text": prefix + blocks[0]["text"]}
    elif prefix:
        blocks.insert(0, {"type": "text", "text": prefix})

    del session[index:]

    logger.debug(
        "    concatenated %d earlier assistant message(s) into the final one",
        len(earlier),
    )
    logger.debug("    earlier text kept: %r", prefix)
    logger.debug("    final blocks: %s", [block["type"] for block in final["content"]])
    logger.debug("    merged blocks: %s", [block["type"] for block in blocks])

    return blocks
