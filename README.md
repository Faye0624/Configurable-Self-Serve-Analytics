# Self-Serve Analytics

A configurable, transparent, self-hostable **self-serve data-analysis** tool.
Non-technical users upload their own data and get insights without writing SQL:

1. **Upload** one or more CSV tables.
2. **Profile & clean** — each column is profiled and basic cleaning is applied;
   anything suspicious is flagged for the user to confirm.
3. **Configure (no code)** — map each column to a *role* (customer / date / amount / …)
   and declare join keys.
4. **Progressive unlock** — analyses (KPIs, cohort / retention, RFM) unlock automatically
   as the data satisfies each template's requirements.
5. **Ask** — query in natural language; the tool shows the **generated SQL** behind every answer.

Because it is **configuration-driven**, the same engine works on a new domain by
configuration alone — no code changes. Demonstrated on the public Olist e-commerce dataset.

## Tech stack

- **Python** + **Streamlit** (UI)
- **DuckDB** — embedded analytical database (no server; stores uploaded tables and runs the
  generated SQL). A thin DB wrapper keeps this swappable (e.g. PostgreSQL for production).
- **LLM** (OpenAI / Anthropic) for the NL→SQL step — added in a later step; a stub is used first.

## Project structure

    self-serve-analytics/
    ├── app/            # Streamlit UI (entry point: app/main.py)
    ├── ssa/            # core package (models, db, services, llm, utils)
    ├── tests/          # unit tests
    ├── requirements.txt
    └── README.md

## Run locally

    python -m venv .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app/main.py

## Status

Built incrementally, one module per commit (see the commit history).
Current: **project scaffold** — runnable UI shell; features added step by step.
