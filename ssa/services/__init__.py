# Services: the logic that operates on the domain model.
from ssa.services.data_registry import DataRegistry, safe_table_name
from ssa.services.profiling import ProfilingService
from ssa.services.cleaning import CleaningService, CleaningOption
from ssa.services.semantic_config import SemanticConfigService
from ssa.services.unlock_engine import UnlockEngine, UnlockResult
from ssa.services.template_engine import TemplateEngine
from ssa.services.sql_guard import SqlGuard, SqlGuardError
from ssa.services.nl_query import NLQueryEngine, QueryResult, HistoryEntry
from ssa.services.project_store import ProjectStore
from ssa.services.auth import AuthService, AuthError

__all__ = [
    "DataRegistry",
    "safe_table_name",
    "ProfilingService",
    "CleaningService",
    "CleaningOption",
    "SemanticConfigService",
    "UnlockEngine",
    "UnlockResult",
    "TemplateEngine",
    "SqlGuard",
    "SqlGuardError",
    "NLQueryEngine",
    "QueryResult",
    "HistoryEntry",
    "ProjectStore",
    "AuthService",
    "AuthError",
]
