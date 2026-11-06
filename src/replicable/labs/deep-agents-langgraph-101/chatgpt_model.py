"""Responses streaming for ChatGPT plan usage, including terminal validation."""
from langchain_openai import ChatOpenAI


class ChatGPTChatModel(ChatOpenAI):
    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=None, **kwargs)
        # ChatGPT plan usage has a narrower contract than API-key Responses.
        # Keep this boundary aligned with Replicable's ImproveOpenAIModel.
        for key in (
            "background", "conversation", "max_output_tokens", "max_tool_calls",
            "max_completion_tokens", "max_tokens", "metadata", "moderation", "multi_agent",
            "prompt", "prompt_cache_retention", "safety_identifier", "temperature",
            "top_logprobs", "top_p", "truncation", "user", "previous_response_id",
            "stream_options", "stop",
        ):
            payload.pop(key, None)
        payload.update(store=False, stream=True)
        for item in payload.get("input", []):
            if item.get("role") == "system":
                item["role"] = "developer"
        tools = payload.get("tools") or []
        if any(tool.get("type") not in {"function", "custom"} for tool in tools):
            raise ValueError("ChatGPT browser mode supports only this lab's client-side tools.")
        if tools:
            payload["tools"] = [{"type": "namespace", "name": "replicable_lab",
                                 "description": "Local teaching, planning, and lab tools.", "tools": tools}]
            choice = payload.get("tool_choice")
            if isinstance(choice, dict) and choice.get("type") in {"function", "custom"}:
                payload["tool_choice"] = {**choice, "namespace": "replicable_lab"}
        return payload

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
