
from typing import Protocol
import json

from google import genai
from google.genai import types

from ..config import settings


class LLM(Protocol):
    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> dict: ...


class GeminiLLM:
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is missing from backend/.env")

        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=30000,
                retry_options=types.HttpRetryOptions(
                    attempts=1
                )
            )
        )

    def complete(self, system, messages, tools):
        gemini_contents = []
        tool_names = {}

        for message_index, message in enumerate(messages):
            role = message["role"]
            content = message["content"]

            if role == "user" and isinstance(content, str):
                gemini_contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=content)]
                    )
                )

            elif role == "assistant":
                parts = []

                for part_index, block in enumerate(content):
                    if block["type"] == "text":
                        parts.append(
                            types.Part.from_text(text=block["text"])
                        )

                    elif block["type"] == "tool_use":
                        tool_id = block["id"]
                        tool_names[tool_id] = block["name"]

                        parts.append(
                            types.Part(
                                function_call=types.FunctionCall(
                                    name=block["name"],
                                    args=block["input"]
                                ),
                                thought_signature=block.get("thought_signature")
                            )
                        )

                if parts:
                    gemini_contents.append(
                        types.Content(role="model", parts=parts)
                    )

            elif role == "user" and isinstance(content, list):
                parts = []

                for block in content:
                    if block["type"] == "tool_result":
                        tool_name = tool_names.get(
                            block["tool_use_id"],
                            "unknown_tool"
                        )

                        try:
                            result = json.loads(block["content"])
                        except (TypeError, json.JSONDecodeError):
                            result = {"result": block["content"]}

                        parts.append(
                            types.Part.from_function_response(
                                name=tool_name,
                                response=result
                            )
                        )

                if parts:
                    gemini_contents.append(
                        types.Content(role="user", parts=parts)
                    )

        function_declarations = [
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters_json_schema=tool["input_schema"]
            )
            for tool in tools
        ]

        config_args = {
            "system_instruction": system,
            "max_output_tokens": 1024,
        }

        if function_declarations:
            config_args["tools"] = [
                types.Tool(function_declarations=function_declarations)
            ]

        response = self._client.models.generate_content(
            model=settings.llm_model,
            contents=gemini_contents,
            config=types.GenerateContentConfig(**config_args)
        )

        content = []
        tool_index = 0

        if response.candidates:
            candidate = response.candidates[0]

            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.text:
                        content.append({
                            "type": "text",
                            "text": part.text
                        })

                    elif part.function_call:
                        call = part.function_call

                        content.append({
                            "type": "tool_use",
                            "id": f"gemini_call_{tool_index}",
                            "name": call.name,
                            "input": dict(call.args or {}),
                            "thought_signature": part.thought_signature
                        })

                        tool_index += 1

        has_tool_calls = any(
            block["type"] == "tool_use" for block in content
        )

        return {
            "stop_reason": "tool_use" if has_tool_calls else "end_turn",
            "content": content
        }


class ScriptedLLM:
    """Fake LLM for tests: returns pre-written responses in order."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.last_tools: list[str] = []

    def complete(self, system, messages, tools):
        self.last_tools = [t["name"] for t in tools]
        return self.responses.pop(0)


def get_llm() -> LLM:
    return GeminiLLM()
