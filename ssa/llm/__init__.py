# LLM layer: the NL->SQL client interface, the schema contract sent to it,
# an offline stub, an optional real (OpenAI) client, and a factory that picks
# one from the environment.
from ssa.llm.base import LLMClient
from ssa.llm.schema import Schema, SchemaColumn, SchemaTable, build_schema
from ssa.llm.stub import StubLLMClient
from ssa.llm.factory import build_default_client

__all__ = [
    "LLMClient",
    "Schema",
    "SchemaColumn",
    "SchemaTable",
    "build_schema",
    "StubLLMClient",
    "build_default_client",
]
