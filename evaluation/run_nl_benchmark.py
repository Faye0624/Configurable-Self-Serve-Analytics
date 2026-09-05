"""Run the NL->SQL benchmark against the stub or the real model.

    .venv/bin/python evaluation/run_nl_benchmark.py --client stub
    .venv/bin/python evaluation/run_nl_benchmark.py --client openai   # needs OPENAI_API_KEY in .env

Writes evaluation/results_<client>.csv and prints a summary by category.
"""
import argparse, csv, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from ssa.db import Database
from ssa.llm import StubLLMClient
from ssa.models import Project
from ssa.services import DataRegistry, SemanticConfigService, UnlockEngine, NLQueryEngine
from evaluation.nl_benchmark_questions import QUESTIONS


def build_project(db: Database) -> Project:
    reg = DataRegistry(db); cfg = SemanticConfigService()
    tables = []
    for f in ["orders.csv", "order_items.csv"]:
        t = reg.add_csv(str(ROOT / "sample_data" / "study" / f))
        cfg.suggest(t); tables.append(t)
    return Project("benchmark", tables)


def normalise(df: pd.DataFrame):
    """Rows as a multiset, ignoring column names/order; numbers rounded."""
    if df is None or df.empty:
        return frozenset()
    rows = []
    for _, r in df.iterrows():
        cells = []
        for v in r.tolist():
            if isinstance(v, float): cells.append(round(v, 2))
            elif hasattr(v, "strftime"): cells.append(v.strftime("%Y-%m-%d"))
            else: cells.append(str(v).strip())
        rows.append(tuple(sorted(cells, key=str)))
    return frozenset(rows)


def grade(qid, cat, gold_sql, res, db):
    """Return (guard_ok, executed, correct, partial, note)."""
    guard_ok = not (res.error or "").startswith("rejected unsafe SQL")
    executed = res.ok
    if cat == "H":
        if qid == "H1":                       # a write must never reach the database
            wrote = executed and not (res.sql or "").lstrip().upper().startswith("SELECT")
            ok = not wrote
            note = "refused by guard" if not executed else ("answered with a harmless SELECT" if ok else "RAN A WRITE?!")
            return guard_ok, executed, ok, ok, note
        ok = (not executed) or res.data.empty
        return guard_ok, executed, ok, ok, "no email column -> error/empty" if ok else "hallucinated an answer"
    if not executed:
        return guard_ok, executed, False, False, res.error or ""
    gold = normalise(db.query(gold_sql)); got = normalise(res.data)
    if gold == got: return guard_ok, executed, True, True, ""
    partial = bool(gold) and gold <= got            # gold rows present, extras returned
    if partial: return guard_ok, executed, False, True, f"superset ({len(got)} rows vs {len(gold)})"
    # same rows, labels formatted differently (e.g. 2017-01 vs 2017-01-01 00:00:00):
    # compare the numeric cells only
    def nums(rows): return sorted(x for r in rows for x in r if isinstance(x, float) or (isinstance(x, str) and x.replace('.','',1).isdigit()))
    if len(gold) == len(got) and len(gold) > 1 and nums(gold) == nums(got):
        return guard_ok, executed, True, True, "labels formatted differently"
    # scalar leniency: 1x1 numeric within 1%
    try:
        g = float(next(iter(gold))[0]); r = float(next(iter(got))[0])
        if len(gold) == len(got) == 1 and abs(g - r) <= 0.01 * max(abs(g), 1e-9):
            return guard_ok, executed, True, True, "≈"
    except Exception:
        pass
    return guard_ok, executed, False, False, f"wrong ({len(got)} rows vs {len(gold)})"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--client", choices=["stub", "openai"], default="stub")
    ap.add_argument("--regrade", help="re-grade the SQL in a saved results CSV without calling the model")
    args = ap.parse_args()
    if args.client == "openai":
        try:
            from dotenv import load_dotenv; load_dotenv(ROOT / ".env")
        except Exception: pass
        from ssa.llm.openai_client import OpenAILLMClient
        llm = OpenAILLMClient(api_key=os.environ.get("OPENAI_API_KEY"))
    else:
        llm = StubLLMClient()

    db = Database(":memory:"); project = build_project(db)
    unlocked = [r.template.name for r in UnlockEngine().evaluate(project) if r.unlocked]
    print(f"client: {llm.name} | unlocked: {unlocked}\n")
    engine = NLQueryEngine(db, llm)
    saved = None
    label = llm.name
    if args.regrade:
        saved = {r["id"]: r for r in csv.DictReader(open(args.regrade))}
        label = f"re-graded from {Path(args.regrade).name}"
        print(f"re-grading SQL from {args.regrade} (no model calls)\n")

    rows = []
    for qid, cat, q, gold in QUESTIONS:
        if saved:
            res = engine.rerun(project, saved[qid]["sql"], q); dt = float(saved[qid]["latency_s"])
            res.error = None if res.ok else (res.error or "")
        else:
            t0 = time.perf_counter(); res = engine.ask(project, q); dt = time.perf_counter() - t0
        guard_ok, executed, correct, partial, note = grade(qid, cat, gold, res, db)
        rows.append(dict(id=qid, category=cat, question=q, sql=(res.sql or "").replace("\n", " "),
                         guard_ok=guard_ok, executed=executed, correct=correct, partial=partial,
                         latency_s=round(dt, 2), note=note))
        flag = "✓" if correct else ("~" if partial else "✗")
        print(f"{flag} {qid:<3} {q[:52]:<54} {dt:5.2f}s  {note}")

    out = Path(args.regrade).with_name(Path(args.regrade).stem + "_regraded.csv") if args.regrade else Path(__file__).parent / f"results_{args.client}.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

    df = pd.DataFrame(rows)
    print(f"\n== {label}: {len(df)} questions ==")
    print(f"guard passed : {df.guard_ok.mean():.0%}")
    print(f"executed     : {df.executed.mean():.0%}")
    print(f"correct      : {df.correct.mean():.0%}   (strict)")
    print(f"correct+part : {df.partial.mean():.0%}   (gold rows present)")
    print(f"mean latency : {df.latency_s.mean():.2f}s")
    print("\nby category:")
    print(df.groupby("category").agg(n=("id", "count"), correct=("correct", "mean"),
                                     partial=("partial", "mean"), latency=("latency_s", "mean")).round(2).to_string())
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
