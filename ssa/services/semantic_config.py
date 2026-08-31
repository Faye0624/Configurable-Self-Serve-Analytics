"""Assigns roles and join keys, and suggests likely ones."""

from ssa.models import Column, DatasetTable, Role


def _is_numeric(dtype: str) -> bool:
    return "int" in dtype or "float" in dtype


class SemanticConfigService:
    ID_HINTS = ("customer", "user", "client", "member", "account")
    DATE_HINTS = ("date", "time", "_at", "timestamp")

    # US6: what this column means.
    def set_role(self, table: DatasetTable, column_name: str, role: Role) -> None:
        self._find(table, column_name).role = role

    # US7: key_name is the shared name matching this table to others.
    def set_join_key(self, table: DatasetTable, column_name: str, key_name: str = "") -> None:
        col = self._find(table, column_name)
        col.is_join_key = True
        col.key_name = key_name or column_name

    # Mirror of set_join_key, so the UI never writes to the model itself.
    def clear_join_key(self, table: DatasetTable, column_name: str) -> None:
        col = self._find(table, column_name)
        col.is_join_key = False
        col.key_name = ""

    # US8: a guess from name + type only — a starting point the user can change.
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
            # using contnue to config next column

            if any(h in name for h in self.DATE_HINTS) or "date" in dtype or "time" in dtype:
                col.role = Role.DATE
            elif _is_numeric(dtype):
                col.role = Role.MEASURE
            else:
                col.role = Role.DIMENSION
             # ↑ There are limitations， may be completed in the future.

    def _find(self, table: DatasetTable, column_name: str) -> Column:
        for col in table.columns:
            if col.name == column_name:
                return col
        raise KeyError(f"column '{column_name}' not found in table '{table.name}'")
