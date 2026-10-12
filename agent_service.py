from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_INSTRUCTIONS = """
You are a Data Readiness Assessment Agent.

Your job is to help a business or technical stakeholder determine whether
enterprise data is ready for CRM, analytics, or AI deployment.

Important rules:

1. Use the readiness assessment tool before making claims about readiness.
2. Never invent scores, metrics, failed checks, or data-quality findings.
3. Explain technical findings in business terms.
4. Distinguish clearly between:
   - observed evidence
   - interpretation
   - recommendation
5. Prioritize recommendations by business impact and implementation effort.
6. Do not expose raw customer records or personally identifiable information.
7. You may recommend remediation, but you must not modify data or trigger
   production actions.
8. If the available assessment does not contain enough evidence, say so.
"""


TOOLS = [
    {
        "type": "function",
        "name": "get_readiness_assessment",
        "description": (
            "Returns the deterministic readiness assessment for the selected "
            "dataset and deployment use case. Use this before answering."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    }
]


def run_readiness_agent(
    user_question: str,
    assessment: dict[str, Any],
) -> str:
    """
    Run one agent turn using the existing deterministic assessment as a tool.

    The assessment is passed into this function from your existing Streamlit
    workflow. The model interprets the assessment; it does not calculate it.
    """

    conversation = [
        {
            "role": "user",
            "content": user_question,
        }
    ]

    response = client.responses.create(
        model=MODEL,
        instructions=SYSTEM_INSTRUCTIONS,
        tools=TOOLS,
        input=conversation,
    )

    # Continue the response if the model requests the assessment tool.
    while True:
        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            return response.output_text

        tool_outputs = []

        for tool_call in tool_calls:
            if tool_call.name == "get_readiness_assessment":
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_call.call_id,
                        "output": json.dumps(
                            assessment,
                            default=str,
                        ),
                    }
                )

        response = client.responses.create(
            model=MODEL,
            instructions=SYSTEM_INSTRUCTIONS,
            tools=TOOLS,
            previous_response_id=response.id,
            input=tool_outputs,
        )
