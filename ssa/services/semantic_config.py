from ssa.models import Column, DatasetTable, Role


def _is_numeric(dtype: str) -> bool:
    return "int" in dtype or "float" in dtype


# Applies the user's no-code configuration to a table: what each column means
# (role) and which columns join it to other tables (join key).
class SemanticConfigService:
    ID_HINTS = ("customer", "user", "client", "member", "account")
    DATE_HINTS = ("date", "time", "_at", "timestamp")

    # Assign a semantic role to a column (US6).
    def set_role(self, table: DatasetTable, column_name: str, role: Role) -> None:
        self._find(table, column_name).role = role

    # Mark a column as a join key (US7). key_name is the shared name used to
    # match this table to others; defaults to the column's own name.
    def set_join_key(self, table: DatasetTable, column_name: str, key_name: str = "") -> None:
        col = self._find(table, column_name)
        col.is_join_key = True
        col.key_name = key_name or column_name

    # Pre-fill likely roles and join keys from column names + types, for the
    # user to confirm or change (US8). Heuristic starting point only.
    def suggest(self, table: DatasetTable) -> None:
        for col in table.columns:
            name = col.name.lower()
            dtype = col.data_type.lower()

            # "id" / "*_id" -> join key; a customer-like id also gets IDENTIFIER.
            if name == "id" or name.endswith("_id"):
                col.is_join_key = True
                col.key_name = col.name
                if any(h in name for h in self.ID_HINTS):
                    col.role = Role.IDENTIFIER
                continue

            if any(h in name for h in self.DATE_HINTS) or "date" in dtype or "time" in dtype:
                col.role = Role.DATE
            elif _is_numeric(dtype):
                col.role = Role.MEASURE
            else:
                col.role = Role.DIMENSION

    def _find(self, table: DatasetTable, column_name: str) -> Column:
        for col in table.columns:
            if col.name == column_name:
                return col
        raise KeyError(f"column '{column_name}' not found in table '{table.name}'")
