"""US19 / NFR-4: point the same engine at a second domain with no code change.

Builds a small synthetic *hospital* dataset (patients + visits), runs it through the
exact same path a user's upload takes — DataRegistry -> suggest() -> UnlockEngine ->
TemplateEngine -> NLQueryEngine(stub) — and reports what unlocked and what ran.
Also times the three templates on the Olist study subset (NFR-3).

    .venv/bin/python evaluation/portability_check.py
"""
import sys, time, random
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
import pandas as pd
from ssa.db import Database
from ssa.llm import StubLLMClient
from ssa.models import Project
from ssa.services import DataRegistry, SemanticConfigService, UnlockEngine, TemplateEngine, NLQueryEngine

def show_unlock(project, label):
    print(f"  [{label}]")
    for r in UnlockEngine().evaluate(project):
        print(f"    {'UNLOCKED' if r.unlocked else 'locked  '}  {r.template.name}  {r.reason}")

def run(project_name, frames, corrections=()):
    db = Database(":memory:"); reg = DataRegistry(db); cfg = SemanticConfigService(); tables = []
    for name, df in frames:
        t = reg.add_dataframe(name, df, source_file=f"{name}.csv"); cfg.suggest(t); tables.append(t)
    project = Project(project_name, tables)
    print(f"\n=== {project_name} ===")
    for t in tables:
        print(f"  {t.name}: " + ", ".join(f"{c.name}[{c.role}{'+key' if c.is_join_key else ''}]" for c in t.columns))
    show_unlock(project, "after automatic suggestion only")
    for table_name, col, role in corrections:          # what a user would do in the role editor
        cfg.set_role(next(t for t in tables if t.name == table_name), col, role)
        print(f"  user sets {table_name}.{col} -> {role}")
    if corrections: show_unlock(project, "after the user's correction")
    eng = TemplateEngine(db); timings = {}
    for label, fn in [("key_metrics", eng.run_key_metrics), ("cohort", eng.run_cohort), ("rfm", eng.run_rfm)]:
        t0 = time.perf_counter(); sql, df = fn(project); timings[label] = time.perf_counter() - t0
        print(f"  {label:<12} {len(df):>4} rows  {timings[label]*1000:6.1f} ms   first row: {df.iloc[0].to_dict() if len(df) else '-'}")
    nl = NLQueryEngine(db, StubLLMClient())
    for q in ["total cost", "how many patients", "average cost by department"]:
        r = nl.ask(project, q); print(f"  NL(stub) '{q}': {'ok' if r.ok else r.error} -> {r.sql}")
    return timings

# ---- second domain: hospital visits (synthetic, deliberately not e-commerce) ----
random.seed(7)
depts = ["cardiology", "orthopaedics", "paediatrics", "oncology", "emergency"]
patients = pd.DataFrame({"patient_id": [f"pt{i:03d}" for i in range(120)],
                         "home_city": [random.choice(["Glasgow", "Edinburgh", "Dundee", "Aberdeen"]) for _ in range(120)]})
visits = pd.DataFrame({
    "visit_id": [f"v{i:04d}" for i in range(500)],
    "patient_id": [f"pt{random.randint(0,119):03d}" for _ in range(500)],
    "admission_date": [f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}" for _ in range(500)],
    "department": [random.choice(depts) for _ in range(500)],
    "treatment_cost": [round(random.uniform(80, 2500), 2) for _ in range(500)],
})
from ssa.models import Role
run("hospital (second domain)", [("patients", patients), ("visits", visits)],
    corrections=[("visits", "patient_id", Role.IDENTIFIER)])

# ---- Olist study subset, for NFR-3 timing ----
orders = pd.read_csv(ROOT / "sample_data/study/orders.csv"); items = pd.read_csv(ROOT / "sample_data/study/order_items.csv")
t = run("olist (study subset)", [("orders", orders), ("order_items", items)])
print(f"\nNFR-3: slowest template on the study subset = {max(t.values())*1000:.0f} ms")
