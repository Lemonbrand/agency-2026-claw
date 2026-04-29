# Agency 2026 · Walk-through

First-person screen share. Three minutes if I keep it tight.

---

## Intro

Agency 2026 is a hackathon on Government of Alberta public data. The brief carries ten accountability questions a public-sector audit committee would love to answer and rarely has the time to.

Zombie recipients (companies that took public money and dissolved twelve months later). Ghost capacity (organisations funded to deliver services with no employees, no premises, nothing but transfer flows in and out). Funding loops between charities. Sole-source amendment creep. Vendor concentration that quietly hardened into incumbency. Related-party networks across the directors of funded entities. Policy commitments versus actual spend. Duplication and gaps across federal, provincial, and municipal ledgers. Contract inflation by category. Adverse media against funded recipients.

A team of analysts would spend weeks on any one of these. An office of analysts would spend years on the full ten. That is why most of these questions never get answered at the scale of a province, let alone a country.

I had one day.

So I gave the brief to a small AI agent team. Three reviewers, three different jobs, working off a read-only copy of the GovAlta Postgres. One human in the loop, which was me. The bill for the day is on the home page in front of you. Hold the number. It comes back at the end and it is half the story.

Walking the app now, page by page.

---

## Home (`/`)

The big number top-left is the AI bill so far today, in Canadian dollars. Live. Refreshes every minute.

Underneath it, the line: one day, AI auditing the Government of Alberta, every dollar routed through US infrastructure. The whole project in a sentence.

The orange box is an open question I want to leave with you. I will come back to it on the sovereign page.

The pie shows which providers the system leaned on. Claude, Codex, OpenRouter. The map plots their cities. Every pie slice connects to a blue dot on US soil. The Canadian dot is red and empty.

Provider cards under the map carry the per-model totals. Claude did the heavy reading and most of the refusing. Codex ran the SQL. OpenRouter handled cheaper drafts on the side. Each model doing what it is good at.

"What it bought" is my curated pick of three review leads from the run. Below that, four cards point at the rest of the app: findings, evidence, ask, sovereign brief. I will go in order.

---

## Findings (`/stories.html`)

The picks at the top are small-amount stories. That is not an accident. The brief, read carefully, is asking what fragmented spending hides.

**Canada Gives.** A registered donation platform. The system found it sitting inside 321 separate qualified-donee gift loops on the CRA file. $4.1 million of circular gift volume on the year. Average loop: $12,800. Not one of those 321 transfers, on its own, would trip a CRA reporting threshold. The pattern only shows up when you map all 321 at once. I wrote on the card directly: platform behaviour, not a red flag. The system itself refused to call it more.

**Three Alberta vendors.** Alberta Blue Cross, B+H Architects, Telus Health. Each one wins the open-bid contracts and the no-bid contracts in their ministry. The buying rules picked them. That is a policy outcome, not a procurement violation. The interesting question I left on the card: does the rest of the market know the door is closed.

**Cross-signal entities.** IBM Canada, TransAlta, Wood Buffalo. Each one came up in two or more separate checks without me telling the system to look. The system flagged itself.

Underneath the picks: the names that came up more than once across checks, three challenges I refused in print, and the searchable table of every lead the system surfaced. Any row opens a detail drawer.

---

## A challenge page (`/challenges/03-funding-loops.html`)

Drilling into Funding Loops, challenge 3 from the brief.

Top of the page is the brief's question, copied in word for word: where does money flow in circles between charities, and does it matter.

Below it, the review lead. Canada Gives, $4.1M circular, 321 loops.

Below the lead is every other entity the system surfaced for this check. Twenty of them, sorted by severity, all clickable. My Charity Fund, 340 loops, $6,800 average. Toronto Foundation, 257 loops. Vancouver Foundation, 185. Different names, same shape. Many small loops, no single one big enough to flag.

The blocks underneath are the receipts. The roadblocks the system named in print. The read-only SQL it actually ran, with runtime, record count, and a fingerprint another reviewer can run from scratch. The countercheck the system imposed on itself. Missing evidence it says it would need to go further. A decision panel where I can mark the lead for escalation.

I kept this page boring on purpose. A reviewer should be able to skim it and trust it.

---

## Evidence trail (`/trust.html`) — why any of this is true

This is the page that earns everything else.

Three AI reviewers, three jobs, set up so they catch each other.

A first reviewer drafts the questions. Eleven checks in parallel. Cheap, fast, and willing to be wrong.

A second reviewer connects to the GovAlta database. Read-only. It verifies every reference the first reviewer makes. It runs the query. It captures runtime, record count, and a fingerprint. If a reference resolves to nothing in the actual schema, the lead gets refused right there.

A third reviewer reviews the evidence, writes the explanation, and refuses anything the data does not support. A lexical audit pass on top of that counts made-up names, fake IDs, and unsupported claims. The verdict numbers at the top of this page (clean, needs review, unsafe) are that audit's tally.

The discipline is in the hand-off, not in any one model. Each model proposes. The next one checks. The evidence trail remembers.

You do not have to take the model's word. The query it ran is captured with runtime and a fingerprint another reviewer can re-run, on the same database, from scratch. The cost is on every page. The lexical audit catches anything in a brief that resolves to nothing in the source data. And the system writes its refusals down, on principle, with the data that would change each answer.

That is the verification loop. It is what lets a small AI team do this kind of work without burning the trust the work depends on.

---

## Sovereign AI (`/sovereignty-dialogue.html`) — the cost callback

Here is where I bring the bill back.

Sixteen hundred Canadian dollars in one day on a working laptop. All of it crossed the border into US data centres. Now hold that against what I just walked you through.

Eleven accountability checks on a province's books. Eighty review leads. Three principled refusals. Receipts on every claim, fingerprints reviewers can re-run. One operator.

Now imagine fifty of those operators inside the office of an auditor general, each running this workflow on a corner of the budget. Or a thousand citizens, each running it on the open dataset for their own riding. Or a Friday cron that runs the whole brief weekly and surfaces what changed since last Friday. The per-check cost approaches negligible. The blind spots that exist today (because no human has time to map all the fragments) stop existing.

That is the proof of concept. A small AI agent team, set up with the right hand-off discipline, makes the brief's questions tractable across all of government. Auditors keep their judgement. Their reach changes.

The brief on this page lays out the path to keep the work Canadian. Demand map first, before concrete. Site and power. Anchor deal. Build and certify. Lane operational.

Today's tools work. Today's bill went south. The conversation that opens, after a demo like this, is what it would take to keep the next $1,600 inside Canadian-controlled compute. And the $1.6 million after that. And the $1.6 billion in public-sector AI workloads after this kind of work is normal.

Municipal, provincial, federal, and infrastructure partners all need to be in the room.

---

## Close

One person, one day, sixteen hundred Canadian dollars of AI work on Alberta. Eleven of the brief's ten questions run end to end. Three refused in print.

The refusals are the receipts. That is where the trust starts.

If one person can do this in a day, the auditor general's office can run it across every department. Provincial accountability committees can run it on every program they oversee. A citizen can run it on the open dataset for their own riding. None of those scenarios are speculative. Today's bill is the proof.

The open question is whether the next dollar of this kind of work runs on Canadian compute or US compute. That question does not get answered by ignoring it.

That is what I want to leave you with.

---

## Numbers to verify the morning of recording

| What | Where | Today |
|---|---|---|
| Total CAD | `overview.json` → `headline_numbers.dollars_today × 1.385` | CA$1,606 |
| Per-provider | `sovereignty.{claude,codex,openrouter}_cost_usd × 1.385` | $1,558 / $39 / $9 |
| Tokens | `sovereignty.claude_tokens_today`, `codex_tokens_today` | 547M / 186M |
| Canada Gives | `findings-index.json` entity `CANADA GIVES` | 321 loops · $4.1M · ~$12.8K avg |
| My Charity Fund | same | 340 loops · $2.3M · ~$6.8K avg |
| Calgary RC SD | `08a-duplicative-overlap` | 4 federal grants ($593K), 2,663 AB payments ($5.05B) |

---

## If asked

**One-shot ChatGPT vs this?**
A one-shot prompt has no receipts. Mine link back to a query, a runtime, a record count, and a fingerprint another reviewer can re-run. A one-shot prompt also does not refuse. I refused three of the ten checks in print. And a one-shot prompt does not show its bill. I show it on every page.

**The policy ask?**
Run sensitive public-sector AI on Canadian-controlled compute. Build the demand side first (workloads, sensitivity tiers, audit needs) before the concrete. Treat anchor demand from government as the financing primitive that makes a Canadian compute lane bankable.

**Why does the support column say "needs reviewer check" on most rows?**
Honest answer: only challenge 5 had its support-audit pass run today. The other findings are indexed but not yet cross-referenced. I made the label say "needs reviewer check" rather than hide the gap.

**Another province?**
Pipeline is dataset-shaped, not Alberta-shaped. Drop a comparable Postgres dump from another jurisdiction in, point the read-only role at it, run the same eleven checks. Anything the new dataset cannot answer gets refused, named, and logged.

**What stops a hostile actor running this against the wrong target?**
The pipeline is structured to refuse, by default. That cuts both ways. It will not invent a finding under pressure. It will not skip refusing because the question is politically convenient.

---

## Elevator

> One person, one day, sixteen hundred Canadian dollars of AI work on Alberta public data. Eleven accountability checks. Three refused on principle. The most useful finding is that this kind of work is now tractable across all of government, and the open question is which side of the border it runs on.
