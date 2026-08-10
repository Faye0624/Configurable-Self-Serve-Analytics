"""A real NL->SQL client backed by an OpenAI chat model (optional).

Used only when an API key is configured (see factory.py); otherwise the offline
stub is used. `openai` is imported lazily so the app runs without the package
installed as long as this client isn't selected.

Privacy (NFR-2): the prompt contains only the schema text (table/column names,
types, roles) and the question — never any data rows.
"""

from ssa.llm.base import LLMClient
from ssa.llm.schema import Schema

_SYSTEM_PROMPT = (
    "You translate a business question into ONE read-only SQL query for DuckDB. "
    "Rules: return a single SELECT statement only (no INSERT/UPDATE/DELETE/DDL, "
    "no comments, no explanation). Use only the tables and columns in the schema. "
    "Quote identifiers with double quotes. "
    "Date/time values stored as TEXT must be CAST before using date functions, "
    'e.g. date_trunc(\'month\', CAST("order_date" AS TIMESTAMP)) or '
    'strftime(CAST("order_date" AS TIMESTAMP), \'%Y-%m\'). '
    "Output SQL only."
)


class OpenAILLMClient(LLMClient):
    name = "OpenAI"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self._model = model
        self._api_key = api_key
        self.name = f"OpenAI ({model})"

    def generate_sql(self, question: str, schema: Schema) -> str:
        from openai import OpenAI  # lazy import: only needed on this path

        client = OpenAI(api_key=self._api_key) if self._api_key else OpenAI()
        response = client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",
                 "content": f"Schema:\n{schema.to_prompt_text()}\n\nQuestion: {question}\n\nSQL:"},
            ],
        )
        return _strip_code_fence(response.choices[0].message.content or "")


# Models sometimes wrap SQL in ```sql ... ``` fences; strip them.
def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    return text.strip().rstrip(";").strip()
