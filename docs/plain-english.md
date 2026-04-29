# Plain English Explainer

LemonClaw is an accountability story engine.

It helps a reviewer take a folder of government datasets and turn it into a short, defensible list of stories worth telling. Some stories are risks worth reviewing. Some are opportunities worth scaling. Some are operating insights that change how a system is understood. The job is to surface them all, classify them honestly, and refuse the ones the data does not support.

It does not replace judgment. It organizes judgment.

## The Human Job

A human auditor starts with questions like:

- Which files did we receive?
- What columns exist?
- Can this data answer the challenge question?
- Which checks are valid?
- Which checks should we reject because the data is missing?
- What looks unusual?
- What would weaken that signal?
- Can another person replay the work?

Most teams jump straight to "find something interesting." That is dangerous. The first job is to decide what the data can actually support.

## The System Job

The system does the same job, but faster:

1. It loads the files.
2. It profiles the schema.
3. It asks Codex which checks are runnable.
4. It records rejected checks with reasons.
5. It runs deterministic SQL skills.
6. It replays the SQL to verify the findings.
7. It asks for counterchecks designed to weaken its own findings.
8. It groups likely related entities.
9. It asks Claude to classify each finding into a story type and write a seven-field story packet.
10. It stores the whole trail in Neotoma.
11. It builds a static HTML dashboard organized into three columns: risks, operating insight, opportunities.

## What Makes It Agentic

The agent is not trusted to do arithmetic or invent findings.

The agent is used where human judgment is normally needed:

- read a new schema
- decide which investigations are possible
- explain why other investigations are not possible
- suggest what could weaken a finding
- warn when wording is too strong

That is the agentic loop. The model makes decisions about the work. The database does the work. The ledger records the work.

## What Makes It Auditable

Every finding carries:

- which table it came from
- which source file hash produced that table
- which SQL generated the signal
- whether the SQL replayed
- which countercheck was run
- whether the countercheck supported or contested the finding
- what language the reviewer recommends

The dashboard is not the source of truth. It is the readable view of the truth packet.

## The Core Message

Public-sector AI should not be a chatbot pasted on top of spreadsheets.

It should be a controlled loop:

- local data
- declared checks
- visible rejections
- replayable SQL
- skeptical review
- durable memory
- clear next action

That is what this repo demonstrates.
