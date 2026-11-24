from .log import logger


def concatenate_interrupted_responses(session, index):
    """Remove a run of continuations from `session` and return their merged content.

    `index` is the position in `session` of the first truncated assistant message.
    From there the messages strictly alternate: assistant, "continue" user,
    assistant, "continue" user, ..., and the FINAL assistant response (the one that
    ended the run) must already be appended, so it is the last message.

    Mutates `session`: every message from `index` onwards is deleted. Returns the
    merged list of content blocks, for the caller to append back as one assistant
    message: `{"role": ASSISTANT, "content": returned_blocks}`.
    """
    assistants = session[index::2]

    # create single response with all the responses blocks
    # redundancy is not problematic we believe for now
    final = session[-1]
    final["content"] = [
        block for assistant in assistants for block in assistant["content"]
    ]

    # erase current turn requests and responses
    del session[index:]

    logger.debug("    joined responses' fragmented text")
    return final["content"]
