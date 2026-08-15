"""Pick the NL->SQL client from the environment.

Configuration is read from, in order: a local `.env` file (development), real
environment variables, and Streamlit secrets (how a deployed app receives its
key). If a key is found the real model is used; otherwise the app falls back to
the offline stub so it always runs. This is the single place that decides which
backend is active.
"""

import os

from ssa.llm.base import LLMClient
from ssa.llm.stub import StubLLMClient


def build_default_client() -> LLMClient:
    _load_dotenv_if_present()
    api_key = _setting("OPENAI_API_KEY")
    if api_key:
        try:
            from ssa.llm.openai_client import OpenAILLMClient

            model = _setting("SSA_LLM_MODEL") or "gpt-4o-mini"
            return OpenAILLMClient(model=model, api_key=api_key)
        except Exception:
            # Missing package or bad config -> stay usable with the stub.
            pass
    return StubLLMClient()


def _setting(name: str) -> str | None:
    """Look up a setting in the environment, then in Streamlit secrets.

    Deployed Streamlit apps have no .env file; their configuration is provided
    through `st.secrets`. Reading secrets is wrapped because the app must also
    run outside Streamlit (tests, scripts), where st.secrets doesn't exist.
    """
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


def _load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass  # python-dotenv is optional; env vars still work without it
