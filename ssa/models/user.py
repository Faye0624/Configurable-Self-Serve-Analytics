from dataclasses import dataclass


# A registered account. The password is never stored — only a salted hash.
@dataclass(frozen=True)
class User:
    username: str
    created_at: str = ""
