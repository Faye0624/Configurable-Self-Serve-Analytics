"""Pick the NL->SQL client from the environment.

If an OpenAI API key is available (directly or via a local .env file) the real
model is used; otherwise we fall back to the offline stub so the app always
runs. This is the single place that decides which backend is active.
"""

import os

from ssa.llm.base import LLMClient
from ssa.llm.stub import StubLLMClient


def build_default_client() -> LLMClient:
    _load_dotenv_if_present()
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            from ssa.llm.openai_client import OpenAILLMClient

            model = os.environ.get("SSA_LLM_MODEL", "gpt-4o-mini")
            return OpenAILLMClient(model=model, api_key=api_key)
        except Exception:
            # Missing package or bad config -> stay usable with the stub.
            pass
    return StubLLMClient()


def _load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass  # python-dotenv is optional; env vars still work without it
