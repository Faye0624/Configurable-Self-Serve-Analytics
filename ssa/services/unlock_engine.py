from dataclasses import dataclass

from ssa.models import AnalysisTemplate, Project, Role, STANDARD_TEMPLATES


@dataclass
class UnlockResult:
    template: AnalysisTemplate
    unlocked: bool
    reason: str = ""


# What is missing, in ordinary words. "needs role(s): measure" was precise but
# meaningless to anyone who does not already know the vocabulary.
#
# The role name stays in brackets because the role editor labels its options
# "measure", "date" and so on: a user told only to add "an amount column" would
# have to guess which of those to pick. How to fix it is left to the line at the
# foot of the dashboard, so each card stays short enough to scan.
_MISSING_ROLE_HELP = {
    Role.MEASURE: "an amount column (measure)",
    Role.DATE: "a date column (date)",
    Role.IDENTIFIER: "a column identifying who or what (identifier)",
    Role.DIMENSION: "a category column to group by (dimension)",
}


# Decides which analysis templates a project has unlocked (US9) and, when
# locked, why (US10). A template unlocks when one connected cluster of tables
# together provides all the roles it needs.
class UnlockEngine:
    def evaluate(self, project: Project, templates=None) -> list[UnlockResult]:
        templates = templates or STANDARD_TEMPLATES
        available = self._available_roles(project)
        clusters = self._cluster_roles(project)  # roles reachable within each join cluster

        results = []
        for t in templates:
            missing = t.required_roles - available
            if missing:
                results.append(UnlockResult(t, False, self._missing_reason(missing)))
            elif any(t.required_roles <= roles for roles in clusters):
                results.append(UnlockResult(t, True))
            else:
                results.append(UnlockResult(t, False,
                    "Needs data from separate files — mark the column they share "
                    "as a key in both."))
        return results

    # "Needs an amount column (measure)."
    def _missing_reason(self, missing: set[Role]) -> str:
        wants = [_MISSING_ROLE_HELP.get(r, str(r)) for r in sorted(missing, key=str)]
        if len(wants) > 1:
            wants = [", ".join(wants[:-1]) + f" and {wants[-1]}"]
        return f"Needs {wants[0]}."

    # Every role assigned somewhere in the project.
    def _available_roles(self, project: Project) -> set[Role]:
        return {c.role for tbl in project.tables for c in tbl.columns
                if c.role != Role.UNASSIGNED}

    # Group tables that share a join key, then list the roles reachable inside
    # each group (a group = tables you can join together).
    def _cluster_roles(self, project: Project) -> list[set[Role]]:
        tables = project.tables
        parent = list(range(len(tables)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        # Union tables that declare the same key name.
        key_to_tables: dict[str, list[int]] = {}
        for idx, tbl in enumerate(tables):
            for col in tbl.columns:
                if col.is_join_key:
                    key_to_tables.setdefault(col.key_name, []).append(idx)
        for idxs in key_to_tables.values():
            for other in idxs[1:]:
                parent[find(other)] = find(idxs[0])

        # Collect the roles present in each connected group.
        clusters: dict[int, set[Role]] = {}
        for idx, tbl in enumerate(tables):
            roles = clusters.setdefault(find(idx), set())
            roles.update(c.role for c in tbl.columns if c.role != Role.UNASSIGNED)
        return list(clusters.values())
