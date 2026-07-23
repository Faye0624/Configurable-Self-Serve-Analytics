from dataclasses import dataclass

from ssa.models import AnalysisTemplate, Project, Role, STANDARD_TEMPLATES


@dataclass
class UnlockResult:
    template: AnalysisTemplate
    unlocked: bool
    reason: str = ""


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
                names = ", ".join(sorted(str(r) for r in missing))
                results.append(UnlockResult(t, False, f"needs role(s): {names}"))
            elif any(t.required_roles <= roles for roles in clusters):
                results.append(UnlockResult(t, True))
            else:
                results.append(UnlockResult(t, False, "columns not joinable - declare a shared key"))
        return results

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
