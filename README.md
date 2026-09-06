# Self-Serve Analytics

**Live app: https://self-serve-analytics.streamlit.app**

A configurable, transparent, self-hostable **self-serve data-analysis** tool.
Non-technical users upload their own data and get insights without writing SQL:

1. **Upload** one or more CSV tables.
2. **Review the data quality** — each column is profiled, anything that looks wrong is
   reported with the offending rows, and *the user decides* whether to clean it. Nothing
   is rewritten without being asked.
3. **Confirm what the columns mean (no code)** — the tool works out a *role* for each
   column (customer / date / amount / category) and the keys that join the tables;
   the user corrects anything it got wrong.
4. **Progressive unlock** — analyses (key metrics, cohort / retention, RFM) unlock automatically
   as the data satisfies each template's requirements, and locked ones say what is missing.
5. **Ask** — query in natural language; the tool shows the **generated SQL** behind every answer.

Because it is **configuration-driven**, the same engine works on a new domain by
configuration alone — no code changes. Demonstrated on the public Olist e-commerce dataset.

## Tech stack

- **Python** + **Streamlit** (UI)
- **DuckDB** — embedded analytical database (no server; stores uploaded tables and runs the
  generated SQL). A thin DB wrapper keeps this swappable (e.g. PostgreSQL for production).
- **sqlglot** — parses the generated SQL into a syntax tree so it can be validated as read-only.
- **LLM** (OpenAI `gpt-4o-mini`, optional) for the NL→SQL step, behind a small interface;
  an offline rule-based stub is used when no API key is set, so the app and the tests run
  without any network access.

## Project structure

    self-serve-analytics/
    ├── app/                  # Streamlit UI (entry point: app/main.py) — thin layer, no business rules
    ├── ssa/                  # core package: models, db, services (engine), llm (model clients)
    ├── tests/                # 126 automated tests (pytest)
    ├── evaluation/           # 30-question NL→SQL benchmark: questions, runner, result files
    ├── sample_data/          # study subset of Olist (two tables) and a synthetic hospital dataset
    ├── docs/                 # user-study task sheet and survey, signed ethics checklist, progress tracker
    ├── CodeList.txt          # every significant module, and whether it was written by me or with AI assistance
    ├── SoftwarePrereqs.txt   # software stack, exact versions, how to install and run
    ├── requirements.txt      # minimum versions;  requirements-lock.txt = exact tested versions
    └── README.md

## Run locally

    python -m venv .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app/main.py

## Run the tests and the benchmark

    pytest -q                                          # 126 cases, about 2 seconds, no network needed
    pytest --cov=ssa --cov=app -q                      # with statement coverage
    python evaluation/run_nl_benchmark.py --client stub    # offline baseline
    python evaluation/run_nl_benchmark.py --client openai  # needs OPENAI_API_KEY in .env

## Status

Complete (MSc IT+ project, submitted September 2026). The app covers the whole path
upload → data-quality review → no-code configuration → progressive-unlock dashboard
(Key metrics / Cohort / RFM) → natural-language querying, with the generated SQL shown,
validated as read-only and re-runnable from the query history. Accounts and multiple
isolated projects support the public instance. Evaluation: 126 automated tests
(92% statement coverage of `ssa`), a 30-question NL→SQL benchmark on the study data
(`gpt-4o-mini` 80% correct against 13% for the offline stub) and a five-participant
user study (mean SUS 82.0). The UI is a thin layer over the `ssa` services — all logic
lives there. The dissertation, the video and this archive are the submitted deliverables.
