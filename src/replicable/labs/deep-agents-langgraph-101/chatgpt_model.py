"""Responses streaming for ChatGPT plan usage, including terminal validation."""
from langchain_openai import ChatOpenAI


class ChatGPTChatModel(ChatOpenAI):
    def _stream(self, *args, **kwargs):
        completed = False
        for chunk in super()._stream(*args, **kwargs):
            status = chunk.message.response_metadata.get("status")
            if status in {"failed", "incomplete"}:
                raise RuntimeError("The ChatGPT response did not complete. Check plan usage in ChatGPT and retry.")
            completed = completed or status == "completed"
            yield chunk
        if not completed:
            raise RuntimeError("ChatGPT stream ended before response.completed. Please retry.")

    async def _astream(self, *args, **kwargs):
        completed = False
        async for chunk in super()._astream(*args, **kwargs):
            status = chunk.message.response_metadata.get("status")
            if status in {"failed", "incomplete"}:
                raise RuntimeError("The ChatGPT response did not complete. Check plan usage in ChatGPT and retry.")
            completed = completed or status == "completed"
            yield chunk
        if not completed:
            raise RuntimeError("ChatGPT stream ended before response.completed. Please retry.")
