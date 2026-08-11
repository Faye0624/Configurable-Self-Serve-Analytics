"""Accounts: registration and login.

Passwords are never stored. Each account keeps a random per-user salt and a
PBKDF2-HMAC-SHA256 hash of the password, and login recomputes the hash and
compares it in constant time. PBKDF2 is in the standard library, so this adds
no dependency and works the same on a laptop and on a deployed host.

Accounts live in a `_users` table in the same DuckDB file as the projects, so
one file holds the whole workspace.
"""

import hashlib
import hmac
import os
import re
from datetime import datetime

from ssa.db import Database
from ssa.models.user import User

_USERS_TABLE = "_users"
_ITERATIONS = 200_000          # PBKDF2 work factor
_SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


class AuthError(Exception):
    """Registration or login was refused, with a message safe to show users."""


class AuthService:
    def __init__(self, db: Database):
        self._db = db
        self._db.execute(
            f'CREATE TABLE IF NOT EXISTS "{_USERS_TABLE}" '
            "(username VARCHAR, salt VARCHAR, password_hash VARCHAR, created_at VARCHAR)"
        )

    # --- registration ------------------------------------------------------ #
    def register(self, username: str, password: str) -> User:
        username = (username or "").strip()
        if not _USERNAME_RE.match(username):
            raise AuthError(
                "Username must be 3–32 characters: letters, numbers, dot, dash or underscore."
            )
        if len(password or "") < MIN_PASSWORD_LENGTH:
            raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if self._find(username) is not None:
            raise AuthError("That username is already taken.")

        salt = os.urandom(_SALT_BYTES).hex()
        created = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._db.execute(
            f'INSERT INTO "{_USERS_TABLE}" VALUES (?, ?, ?, ?)',
            [username, salt, _hash(password, salt), created],
        )
        return User(username=username, created_at=created)

    # --- login ------------------------------------------------------------- #
    def login(self, username: str, password: str) -> User:
        row = self._find((username or "").strip())
        # Same message either way, so the form doesn't reveal which usernames exist.
        if row is None or not hmac.compare_digest(
            _hash(password, row["salt"]), row["password_hash"]
        ):
            raise AuthError("Incorrect username or password.")
        return User(username=row["username"], created_at=row["created_at"])

    def user_count(self) -> int:
        return int(self._db.query(f'SELECT COUNT(*) AS n FROM "{_USERS_TABLE}"').iloc[0]["n"])

    # --- internals ---------------------------------------------------------- #
    def _find(self, username: str):
        rows = self._db.query(
            f'SELECT username, salt, password_hash, created_at FROM "{_USERS_TABLE}" '
            "WHERE username = ?",
            [username],
        )
        return None if rows.empty else rows.iloc[0]


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", (password or "").encode(), bytes.fromhex(salt), _ITERATIONS
    ).hex()
