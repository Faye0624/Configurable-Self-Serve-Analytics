# The NL->SQL client layer: interface, schema contract, stub, real client, factory.
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
