"""An account — it holds no password field."""

from dataclasses import dataclass


@dataclass(frozen=True)


class User:
    username: str
    created_at: str = ""
