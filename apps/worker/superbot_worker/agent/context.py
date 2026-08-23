from __future__ import annotations

from superbot_api.domain.models import ToolDescriptor


def tool_descriptors_to_openai(
    descriptors: list[ToolDescriptor],
) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": descriptor.name,
                "description": descriptor.description,
                "parameters": descriptor.input_schema,
            },
        }
        for descriptor in descriptors
    ]
