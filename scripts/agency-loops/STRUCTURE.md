# Required research-brief.md structure

Every loop produces ONE markdown file: `research-brief.md`. Six sections, each at least 200 words, each grounded in real sources. The deliverable is not the analysis output. It is the proof that an AI agent could complete the analysis given the right data.

## Section 1: Build Approach
How an agent solves this challenge end-to-end. Algorithmic choices stated in plain language, then made concrete with pseudo-SQL, scoring formulas, and threshold values. Reference the specific GovAlta tables you would query.

## Section 2: Data Required (and what's missing)
Every field needed, marked **AVAILABLE** (in the GovAlta hackathon datasets — CRA / FED / AB / general schemas) or **MISSING**. For each AVAILABLE field, name `schema.table.column`. For each MISSING field, state precisely what the gap is.

## Section 3: Potential Sources for Missing Data
For every MISSING field, name the authoritative public Canadian source: dataset URL, government publication, regulator, registry, or open data portal. Include the data licence, refresh cadence, and access friction (free / signup / FOI request / paid). No hallucinated URLs.

## Section 4: Methodology
Step-by-step pipeline. What runs, in what order, with what guardrails. Include:
- ingestion + normalization steps
- the analysis stages
- the disconfirming check ("what would prove this finding wrong")
- the false-positive risk language and the cohort comparison strategy

## Section 5: Observability and Provability
Metrics that surface during the run and prove it is working. Examples: rows scanned, hypotheses tested, candidates filtered, false-positive rate against a known cohort, replay success rate, citation density per claim. State the dashboards, counters, and log lines a reviewer would see.

## Section 6: Citation Pack (jury-ready)
Provenance pack a journalist or auditor would need to trust a single finding. List the exact elements:
- source dataset name + version + retrieval timestamp
- schema.table.column with row primary key
- SQL hash + replay command
- regulator dictionary citation (form line, dictionary version)
- counter-source confirmation
Provide one fully-worked example using a real public Canadian dataset and a real form line or regulation.

## Done condition
When every section meets that bar, write `<status>COMPLETE</status>` as the very first line of research-brief.md. Otherwise keep iterating.
