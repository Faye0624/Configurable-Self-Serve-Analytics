"""A daily cap on calls to the language model.

A deployed instance shares one API key across everyone who signs up, so an
unbounded number of questions would be someone else's bill. The limiter counts
model calls per day in the database and refuses further ones once the cap is
reached; the app then falls back to explaining that the limit is reached rather
than failing.

Counting lives in the database (not in memory) so the cap survives restarts and
holds across sessions.
"""

from datetime import date

from ssa.db import Database

_USAGE_TABLE = "_llm_usage"


class DailyLimitReached(Exception):
    """Raised when today's allowance of model calls is used up."""


class UsageLimiter:
    def __init__(self, db: Database, daily_limit: int = 100):
        self._db = db
        self.daily_limit = daily_limit
        self._db.execute(
            f'CREATE TABLE IF NOT EXISTS "{_USAGE_TABLE}" (day VARCHAR, calls INTEGER)'
        )

    def used_today(self) -> int:
        rows = self._db.query(
            f'SELECT calls FROM "{_USAGE_TABLE}" WHERE day = ?', [self._today()]
        )
        return 0 if rows.empty else int(rows.iloc[0]["calls"])

    def remaining_today(self) -> int:
        return max(0, self.daily_limit - self.used_today())

    def check(self) -> None:
        """Raise if the cap is reached; call before spending a model request."""
        if self.remaining_today() <= 0:
            raise DailyLimitReached(
                f"the daily limit of {self.daily_limit} AI questions has been "
                "reached — please try again tomorrow"
            )

    def record(self) -> None:
        """Count one model call against today's allowance."""
        today = self._today()
        if self.used_today() == 0:
            self._db.execute(f'INSERT INTO "{_USAGE_TABLE}" VALUES (?, 1)', [today])
        else:
            self._db.execute(
                f'UPDATE "{_USAGE_TABLE}" SET calls = calls + 1 WHERE day = ?', [today]
            )

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()
