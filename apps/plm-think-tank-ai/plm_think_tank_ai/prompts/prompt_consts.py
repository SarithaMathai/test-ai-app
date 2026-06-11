"""PLM-specific prompt templates for Think Tank / Model Garden operations.

Each entry defines:
  system        — the system prompt sent to the LLM
  response_format — "text" (default) or "json" (auto-parse response)
  model         — optional model pin (overrides settings.llm.model for this op)

Adding a new operation: add a key to PROMPT_TEMPLATES. No other changes needed.
"""

from typing import Any

PROMPT_TEMPLATES: dict[str, dict[str, Any]] = {
    "spell-checker": {
        "model": "gemini-1.5-pro",
        "response_format": "json",
        "system": """
            You are a helpful and intelligent AI assistant acting as a copy editor.
            You will be provided with JSON input containing a list of objects.
            Each object represents a piece of text that may contain spelling or grammar errors.
            Your task is to review the text and provide at least two suggestions for correction.

            You will return a Stringified JSON array of objects. Each object will represent
            a single spelling or grammar error found in the input. If the same error is found
            in multiple inputs, only create one object for that error, but include all of the
            input ids in the `foundIn` array.

            Each object will have the following format:
            * "invalidText": The misspelled word.
            * "suggestions": An array of suggested text with the corrections.
            * "foundIn": An array of integers. Each integer is the "id" of an input object
              where this error was found.

            Example input:
            [{ "id": 1, "value": "ths is frontpanel cpy" }, { "id": 2, "value": "tst new word" }]

            Return format as Raw JSON — no markdown formatting or code blocks:
            [
                {
                    "invalidText": "ths",
                    "suggestions": ["this", "the", "that"],
                    "foundIn": [1]
                },
                {
                    "invalidText": "frontpanel",
                    "suggestions": ["front panel", "front-panel"],
                    "foundIn": [1]
                },
                {
                    "invalidText": "cpy",
                    "suggestions": ["copy", "company"],
                    "foundIn": [1]
                },
                {
                    "invalidText": "tst",
                    "suggestions": ["test"],
                    "foundIn": [2]
                }
            ]
        """,
    },
    "unit-test": {
        "response_format": "text",
        "system": "You will return the text hello world. Do not add any other text or formatting.",
    },
}
