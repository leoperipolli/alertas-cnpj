# alertas-cnpj

A data pipeline over Brazil's open company registry (Receita Federal's *Dados Abertos CNPJ*) and a bot that turns it into two chart posts a day about new businesses: which states, cities and sectors are opening the most companies.

## The problem

The Receita Federal publishes the full CNPJ registry once a month: about 6 GB of zipped CSVs with tens of millions of records, with no API and a layout that changes from time to time. The data answers good questions ("where are the most pet shops opening?"), but it is too big to open in a spreadsheet and easy to read wrong.

## How it works

```mermaid
flowchart LR
    RF[Receita Federal<br/>monthly dump] -->|resumable download| ETL[ETL<br/>DuckDB on local CSVs]
    ETL --> SAN{sanity checks}
    SAN -->|pass| AGG[(weekly aggregate<br/>parquet, in git)]
    AGG --> BOT[bot<br/>GitHub Actions, 2x/day]
    BOT --> R[chart render<br/>matplotlib]
    R --> PUB[X / Telegram]
```

**Monthly ETL, run locally**
- Downloads the monthly extraction with HTTP Range requests, so a dropped connection resumes instead of restarting.
- Registers DuckDB views over the raw CSVs, reads everything as text and casts in SQL. Letting the engine guess types is how a silent layout change turns into bad data.
- Keeps only newly opened, active companies and aggregates them by week × state × city × CNAE (sector).
- Writes a small parquet file that is committed to the repo. That file is the only thing the bot reads, so the bot needs no database or server.

**Daily bot, on GitHub Actions**
- Two cron runs a day, each drawing from its own queue: a "counterintuitive" post in the morning and a "classic" ranking in the evening.
- One monthly dataset feeds a daily schedule through a catalog of parameterized *cuts* (ranking by state, per capita, by sector, by city…). A JSON state file, committed back by the workflow, makes sure no cut repeats until the queue is empty, and the queue resets when new data arrives.
- Renders each post as a PNG chart and publishes through a `Publisher` interface: X, Telegram, or a local file, depending on which secrets are set.

## Data quality

The main risk is not code that crashes. It is code that runs and is wrong, and nobody notices for weeks. `etl/sanity.py` has hard checks that stop the pipeline and soft checks that print numbers to review:

- **Order of magnitude:** Brazil opens roughly 300–400k companies a month. A result far off that range means the parse broke.
- **Reactivation trap:** a suspended company that becomes active again has a recent status date but an old opening date. It is not new, so the filter uses the opening date.
- **Partial weeks:** the last week before the monthly cutoff is incomplete and never goes into a post, so the bot never reports a fake 60% drop.
- **Spot check:** sample CNPJs are printed so they can be checked against a public registry lookup.

## Design decisions

- **No personal data by construction.** The partners (*Sócios*) file is never downloaded. It is left out of the layout allowlist, and a check fails if one shows up on disk.
- **Curated sector names.** Official CNAE descriptions never use everyday words: there is no CNAE for "barbershop" or "pizzeria". A hand-made map links friendly names to codes, because text search fails on exactly the words people share.
- **Per capita cuts** use 2022 IBGE census population, so the charts aren't always led by São Paulo.
- **Charts built for the feed:** a single color per series, a light surface that works in both light and dark themes, and colorblind-safe contrast.

## Stack

Python 3.12 · DuckDB · Parquet · matplotlib · GitHub Actions (cron) · X API (tweepy) / Telegram Bot API

## Structure

- `etl/`: download, load, new-company filter, weekly aggregate, sanity checks, layout per registry version
- `bot/`: cut catalog, scheduling queue, data access, chart theme and render, publishers
- `data/`: the committed aggregate and the queue state
- `.github/workflows/post.yml`: the two daily runs
