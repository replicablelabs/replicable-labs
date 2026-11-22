from ..api import request


def concatenate_interrupted_responses(session, index):
    """Collapse a run of continuations into one assistant message.

    `index` is the position in `session` of the first truncated assistant message.
    From there the messages strictly alternate: assistant, "continue" user,
    assistant, "continue" user, ..., and the FINAL assistant response (the one that
    ended the run) must already be appended, so it is the last message.

    Every block must already be a dict (see `blocks_to_dicts`). The earlier
    assistant messages are text-only (their `tool_use` blocks were stripped). Their
    text is concatenated, with no separator, onto the first text block of the final
    response; any other blocks of the final response (e.g. a `tool_use`) are kept
    in order. The "continue" user messages are dropped.

    Returns a new list; `session` is not modified. If `index` is None, returns
    `session` unchanged.
    """
    if index == len(session):
        return session

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

    return session[:index] + [{"role": request.Role.ASSISTANT, "content": blocks}]
