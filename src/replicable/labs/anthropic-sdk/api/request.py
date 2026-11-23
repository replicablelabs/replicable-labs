"""Values you send to `client.messages.create`. All StrEnums: they compare equal to the API's plain strings."""

from enum import StrEnum


class Role(StrEnum):
    """`messages[].role`. The first message must be USER; system text goes in the top-level `system`."""

    USER = "user"
    ASSISTANT = "assistant"


class BlockType(StrEnum):
    """`type` of a content block you build yourself inside a message's `content` list.

    Only the ones this kata sends; the SDK has more (image, document, ...).
    """

    TEXT = "text"
    TOOL_RESULT = "tool_result"
