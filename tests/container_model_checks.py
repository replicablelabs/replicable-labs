"""Run inside the lab image with PYTHONPATH=/app; no external requests."""
import json
import os
import unittest
from unittest.mock import patch

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

import app
from chatgpt_model import ChatGPTChatModel


def events(text="Hello", *, function=False, terminal="completed"):
    if function:
        item = {"id": "fc_test", "type": "function_call", "call_id": "call_test", "name": "explain_concept",
                "arguments": json.dumps({"concept": "LangGraph"}), "status": "completed"}
        chunks = [
            {"type": "response.output_item.added", "output_index": 0, "item": {**item, "arguments": ""}},
            {"type": "response.function_call_arguments.delta", "output_index": 0, "item_id": "fc_test", "delta": item["arguments"]},
            {"type": "response.output_item.done", "output_index": 0, "item": item},
        ]
    else:
        item = {"id": "msg_test", "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}]}
        chunks = [
            {"type": "response.output_item.added", "output_index": 0, "item": {**item, "content": []}},
            {"type": "response.content_part.added", "output_index": 0, "content_index": 0, "item_id": "msg_test",
             "part": {"type": "output_text", "text": "", "annotations": []}},
            {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "item_id": "msg_test", "delta": text, "logprobs": []},
            {"type": "response.output_item.done", "output_index": 0, "item": item},
        ]
    response = {"id": "resp_test", "object": "response", "created_at": 0, "model": "test-model",
                "status": terminal, "output": [item], "tools": [], "parallel_tool_calls": True,
                "tool_choice": "auto", "error": None,
                "usage": {"input_tokens": 10, "output_tokens": 1, "total_tokens": 11,
                          "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 0}}}
    if terminal:
        chunks.append({"type": "response." + terminal, "response": response})
    return "".join("data: " + json.dumps({**chunk, "sequence_number": index}) + "\n\n" for index, chunk in enumerate(chunks))


class ModelIntegrationTests(unittest.TestCase):
    def test_project_tracing_does_not_inherit_an_incomplete_agent_address(self):
        with patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key", "LANGSMITH_AGENT_ID": "",
                                    "LANGSMITH_AGENT_ENVIRONMENT": "local", "LANGSMITH_PROJECT": "test-project"}, clear=True):
            app.configure_langsmith()
            self.assertNotIn("LANGSMITH_AGENT_ID", os.environ)
            self.assertNotIn("LANGSMITH_AGENT_ENVIRONMENT", os.environ)
            self.assertEqual(os.environ["LANGSMITH_PROJECT"], "test-project")

    def test_agent_tracing_defaults_environment_only_when_an_agent_is_set(self):
        with patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key", "LANGSMITH_AGENT_ID": "test-agent",
                                    "LANGSMITH_AGENT_ENVIRONMENT": "", "LANGSMITH_PROJECT": "legacy-project"}, clear=True):
            app.configure_langsmith()
            self.assertEqual(os.environ["LANGSMITH_AGENT_ENVIRONMENT"], "local")
            self.assertNotIn("LANGSMITH_PROJECT", os.environ)

    def model(self, handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        return ChatGPTChatModel(model="test-model", api_key=lambda: "test-oauth-access", http_client=client,
                                base_url="https://api.openai.com/v1", use_responses_api=True, streaming=True,
                                store=False, use_previous_response_id=False, temperature=None, max_retries=0,
                                include=["reasoning.encrypted_content"], output_version="responses/v1")

    def test_oauth_model_uses_responses_bearer_streaming_and_no_storage(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=events())
        result = self.model(handler).invoke([HumanMessage(content="hello")])
        self.assertEqual(result.text, "Hello")
        self.assertEqual(str(requests[0].url), "https://api.openai.com/v1/responses")
        self.assertEqual(requests[0].headers["authorization"], "Bearer test-oauth-access")
        body = json.loads(requests[0].content)
        self.assertIs(body["stream"], True)
        self.assertIs(body["store"], False)
        self.assertNotIn("temperature", body)
        self.assertNotIn("previous_response_id", body)

    def test_interrupted_stream_is_not_reported_as_success(self):
        model = self.model(lambda request: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=events(terminal=None)))
        with self.assertRaisesRegex(RuntimeError, "before response.completed"):
            model.invoke("hello")

    def test_incomplete_response_is_not_reported_as_success(self):
        model = self.model(lambda request: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=events(terminal="incomplete")))
        with self.assertRaises(RuntimeError):
            model.invoke("hello")

    def test_outer_graph_and_deep_agent_complete_a_real_tool_loop(self):
        requests = []
        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  content=events(function=len(requests) == 1))
        model = self.model(handler)
        with patch.object(app, "model_from_environment", return_value=model), patch.object(app, "read_notes", return_value="LangGraph controls the workflow."):
            result = app.build_graph().invoke({"question": "Use explain_concept to explain LangGraph."})
        self.assertEqual(result["answer"], "Hello")
        self.assertEqual(len(requests), 2)
        for body in requests:
            self.assertNotIn("system", [item.get("role") for item in body["input"]])
            self.assertIn("developer", [item.get("role") for item in body["input"]])
            self.assertTrue(all(tool["type"] == "namespace" for tool in body["tools"]))
        self.assertTrue(any(item.get("type") == "function_call_output" for item in requests[1]["input"]))

    def test_system_messages_and_tool_choice_follow_browser_route_contract(self):
        requests = []
        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=events())
        model = self.model(handler).bind_tools([app.explain_concept], tool_choice="explain_concept")
        model.invoke([SystemMessage(content="Teach the learner."), HumanMessage(content="Hello")])
        self.assertEqual(requests[0]["input"][0]["role"], "developer")
        namespace = requests[0]["tools"][0]
        self.assertEqual(namespace["type"], "namespace")
        self.assertEqual(namespace["tools"][0]["name"], "explain_concept")
        self.assertEqual(requests[0]["tool_choice"]["namespace"], namespace["name"])

    def test_unsupported_preview_fields_are_removed(self):
        model = self.model(lambda request: None)
        body = model._get_request_payload(
            [SystemMessage(content="Teach."), HumanMessage(content="Hello")],
            temperature=0.5, max_output_tokens=20, metadata={"lesson": "one"},
            previous_response_id="resp_old", stop=["STOP"], top_p=0.8, store=True,
        )
        for key in ("temperature", "max_output_tokens", "metadata", "previous_response_id", "stop", "top_p"):
            self.assertNotIn(key, body)
        self.assertIs(body["store"], False)
        self.assertIs(body["stream"], True)


class AsyncModelIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_oauth_stream_requires_completion(self):
        for terminal in ("completed", None):
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=events(terminal=terminal))
            )) as client:
                model = ChatGPTChatModel(model="test-model", api_key=lambda: "test-oauth-access", http_async_client=client,
                                        use_responses_api=True, streaming=True, store=False, temperature=None, max_retries=0)
                if terminal:
                    self.assertEqual((await model.ainvoke("hello")).text, "Hello")
                else:
                    with self.assertRaisesRegex(RuntimeError, "before response.completed"):
                        await model.ainvoke("hello")


if __name__ == "__main__":
    unittest.main(verbosity=2)
