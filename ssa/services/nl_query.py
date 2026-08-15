"""Natural-language query engine (US15-US18, US22).

Pipeline for a question:
    build schema (structure only, no data rows — NFR-2)
      -> LLM turns question + schema into candidate SQL
      -> SqlGuard validates it is a read-only SELECT over known tables (NFR-1)
      -> execute read-only and return the rows + the SQL that produced them.

Every answer carries the generated SQL so the UI can show and download it
(US16). Answered queries are kept in a history that stores the *SQL* (not the
natural-language question) so a query can be replayed by executing the stored
SQL directly — no model call (US22). Any failure is returned as a message
rather than raised, so the UI can ask the user to rephrase (US17).
"""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from ssa.db import Database
from ssa.llm.base import LLMClient
from ssa.llm.schema import build_schema
from ssa.services.sql_guard import SqlGuard, SqlGuardError

# Table that the durable query log lives in, inside the (optional) history DB.
_HISTORY_TABLE = "_query_history"


@dataclass
class QueryResult:
    question: str
    sql: str | None = None
    data: pd.DataFrame | None = None
    error: str | None = None
    from_cache: bool = False  # True when replayed from history (no model call)

    @property
    def ok(self) -> bool:
        return self.error is None and self.data is not None


@dataclass
class HistoryEntry:
    question: str
    sql: str  # the reusable, downloadable artifact
    when: str


class NLQueryEngine:
    MAX_ROWS = 5000  # cap returned rows so a broad query can't flood the UI

    def __init__(self, db: Database, llm: LLMClient, guard: SqlGuard | None = None,
                 history_db: Database | None = None, limiter=None):
        self._db = db
        self._llm = llm
        self._guard = guard or SqlGuard()
        # Optional cap on model calls, used by a deployed instance where one
        # API key is shared by everyone who signs up.
        self._limiter = limiter
        # Optional durable store for the query log (US22). When given, history
        # survives restarts; when None, it lives only in memory for this session.
        self._history_db = history_db
        self.history: list[HistoryEntry] = []
        if history_db is not None:
            self._ensure_history_table()
            self.history = self._load_history()

    @property
    def backend_name(self) -> str:
        return getattr(self._llm, "name", "llm")

    # The exact text that will be sent to the model — shown to the user so they
    # can see that only the schema (no data) leaves the machine (US18).
    def schema_prompt(self, project) -> str:
        return build_schema(project).to_prompt_text()

    # US15/US16: answer a natural-language question.
    def ask(self, project, question: str) -> QueryResult:
        schema = build_schema(project)

        if self._limiter is not None:
            try:
                self._limiter.check()
            except Exception as exc:
                return QueryResult(question, error=str(exc))

        try:
            raw_sql = self._llm.generate_sql(question, schema)
        except Exception as exc:
            return QueryResult(question, error=f"the model could not produce SQL: {exc}")
        if self._limiter is not None:
            self._limiter.record()

        try:
            safe_sql = self._guard.validate(raw_sql, schema.table_names())
        except SqlGuardError as exc:
            return QueryResult(question, sql=raw_sql, error=f"rejected unsafe SQL: {exc}")

        try:
            data = self._execute(safe_sql)
        except Exception as exc:
            return QueryResult(question, sql=safe_sql, error=f"couldn't run the query: {exc}")

        self._record(HistoryEntry(question, safe_sql, _timestamp()))
        return QueryResult(question, sql=safe_sql, data=data)

    # US22: replay a stored query by running its SQL directly — no model call.
    # Still re-validated, so a saved query stays safe if the schema changed.
    def rerun(self, project, sql: str, question: str = "(saved query)") -> QueryResult:
        allowed = build_schema(project).table_names()
        try:
            safe_sql = self._guard.validate(sql, allowed)
        except SqlGuardError as exc:
            return QueryResult(question, sql=sql, error=f"saved SQL no longer valid: {exc}",
                               from_cache=True)
        try:
            data = self._execute(safe_sql)
        except Exception as exc:
            return QueryResult(question, sql=safe_sql, error=f"couldn't run the query: {exc}",
                               from_cache=True)
        return QueryResult(question, sql=safe_sql, data=data, from_cache=True)

    # Read-only execution. Safety is guaranteed upstream by the guard (the SQL
    # is a single SELECT); here we just run it and cap the row count.
    def _execute(self, sql: str) -> pd.DataFrame:
        return self._db.query(sql).head(self.MAX_ROWS)

    # -- durable query log (US22) ----------------------------------------- #
    # The log is a table in a separate history DB, not the analytical DB, so it
    # is never visible to user queries (the guard's allow-list is the project
    # schema, which does not include this table).
    def _ensure_history_table(self) -> None:
        self._history_db.execute(
            f'CREATE TABLE IF NOT EXISTS "{_HISTORY_TABLE}" '
            "(asked_at VARCHAR, question VARCHAR, generated_sql VARCHAR)"
        )

    def _load_history(self) -> list[HistoryEntry]:
        rows = self._history_db.query(
            f'SELECT asked_at, question, generated_sql FROM "{_HISTORY_TABLE}" '
            "ORDER BY rowid DESC"
        )
        return [HistoryEntry(r.question, r.generated_sql, r.asked_at)
                for r in rows.itertuples()]

    def _record(self, entry: HistoryEntry) -> None:
        self.history.insert(0, entry)  # newest first, in memory
        if self._history_db is not None:
            self._history_db.execute(
                f'INSERT INTO "{_HISTORY_TABLE}" (asked_at, question, generated_sql) '
                "VALUES (?, ?, ?)",
                [entry.when, entry.question, entry.sql],
            )


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")
