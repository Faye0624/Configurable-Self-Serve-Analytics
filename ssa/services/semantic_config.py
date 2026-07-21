from ssa.models import Column, DatasetTable, Role


# Applies the user's no-code configuration to a table: what each column means
# (role) and which columns join it to other tables (join key).
class SemanticConfigService:
    # Assign a semantic role to a column (US6).
    def set_role(self, table: DatasetTable, column_name: str, role: Role) -> None:
        self._find(table, column_name).role = role

    # Mark a column as a join key (US7). key_name is the shared name used to
    # match this table to others; defaults to the column's own name.
    def set_join_key(self, table: DatasetTable, column_name: str, key_name: str = "") -> None:
        col = self._find(table, column_name)
        col.is_join_key = True
        col.key_name = key_name or column_name

    def _find(self, table: DatasetTable, column_name: str) -> Column:
        for col in table.columns:
            if col.name == column_name:
                return col
        raise KeyError(f"column '{column_name}' not found in table '{table.name}'")
