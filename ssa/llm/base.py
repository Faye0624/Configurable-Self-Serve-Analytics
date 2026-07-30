"""The LLM client interface used by the NL->SQL engine.

Keeping this behind an interface means the engine doesn't care whether the SQL
comes from an offline rule-based stub (for tests/demos) or a real model — they
are swapped by configuration.
"""

from abc import ABC, abstractmethod

from ssa.llm.schema import Schema


class LLMClient(ABC):
    """Turns a natural-language question + a Schema into a single SQL string.

    Contract for every implementation:
      * it receives only the question and the Schema (structure only, no data
        rows — NFR-2);
      * it returns one SQL statement as text. It does NOT need to guarantee the
        SQL is safe or correct — that is the SqlGuard's job downstream.
    """

    name = "llm"

    @abstractmethod
    def generate_sql(self, question: str, schema: Schema) -> str:
        ...
