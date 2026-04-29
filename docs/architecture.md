# Architecture

LemonClaw separates speed from truth.

DuckDB is the speed layer. It handles raw files and large joins locally.

Neotoma is the truth layer. It stores the small set of decisions, findings, checks, and review records that need to survive the run.

Codex and Claude sit around the deterministic layer. They help select and challenge the work. They do not replace the replayable work.

## Component Graph

```mermaid
flowchart LR
    subgraph Input["Input"]
        Raw[Raw datasets]
        Registry[Skill registry]
    end

    subgraph ModelJudgment["Model judgment"]
        Planner[Codex planner]
        Counter[Codex countercheck planner]
        Reviewer[Claude second pass]
    end

    subgraph Deterministic["Deterministic execution"]
        Onboard[Dataset onboarder]
        Duck[DuckDB]
        Skills[SQL skills]
        Verify[Replay verifier]
        Correlate[Correlation]
    end

    subgraph Memory["Audit memory"]
        Ledger[Local Neotoma]
        State[JSON state files]
    end

    subgraph Output["Output"]
        Queue[Action queue]
        HTML[Static HTML dashboard]
    end

    Raw --> Onboard
    Onboard --> Duck
    Onboard --> State
    Registry --> Planner
    State --> Planner
    Planner --> Skills
    Planner --> State
    Duck --> Skills
    Skills --> Verify
    Skills --> Counter
    Counter --> Duck
    Verify --> Correlate
    Counter --> Correlate
    Correlate --> Reviewer
    Reviewer --> Ledger
    State --> Ledger
    Correlate --> Ledger
    Ledger --> HTML
    Correlate --> Queue
    Queue --> HTML
```

## Trust Boundaries

```mermaid
flowchart TB
    M[Model output] -->|proposal only| P[Plan, rejection, countercheck, wording]
    P --> D[DuckDB execution]
    D --> R[Replayable result]
    R --> V[Verifier]
    V --> N[Neotoma record]
    N --> H[HTML view]

    M -. not trusted as fact .-> X[No standalone claims]
    D -->|trusted if replayable| T[Review lead]
```

Models can propose:

- run this skill
- reject that skill
- try this countercheck
- use safer wording

Models cannot create final truth by themselves.

## Skill Registry

Each skill declares what it needs before it can run.

```mermaid
classDiagram
    class Skill {
        name
        command
        status
        priority
        description
        required fields
        optional fields
        disconfirming checks
    }

    class Planner {
        schema profile
        applicability matrix
        selected skills
        rejected skills
    }

    class Detector {
        SQL
        evidence rows
        finding record
    }

    Skill --> Planner
    Planner --> Detector
```

This is why rejection is visible. If the data has no dissolution date, the zombie-recipient check is rejected. If there is no transfer graph, funding-loop analysis is rejected. That is not a failure. That is audit discipline.

## Data Flow

```mermaid
flowchart TD
    A[data/raw] --> B[File manifest]
    A --> C[DuckDB table]
    C --> D[Schema profile]
    D --> E[Investigation plan]
    E --> F[Selected SQL detectors]
    F --> G[Findings]
    G --> H[Verification replay]
    G --> I[Disconfirming checks]
    G --> J[Entity clusters]
    H --> K[Correlated queue]
    I --> K
    J --> K
    K --> L[Reviewer packet]
    L --> M[Neotoma audit packet]
    M --> N[web/dashboard.html]
```

## Why Local-First

The demo path is laptop-local because the event environment is unpredictable.

Local-first means:

- no VPS dependency
- no remote database dependency
- no venue Wi-Fi dependency for the HTML presentation
- raw event files do not need to leave the laptop
- the audit packet can be pushed later if appropriate

The model-assisted preparation path can use Codex and Claude through local subscription CLIs. The presentation does not require those calls to be live.
