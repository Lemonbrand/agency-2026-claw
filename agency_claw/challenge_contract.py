from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Challenge:
    id: int
    slug: str
    loop_dir: str
    name: str
    status_default: str
    artifact_type: str
    challenge_statement: str
    ai_native_pattern: str
    direct_tables: tuple[str, ...]
    roadblocks: tuple[str, ...]
    finding_challenges: tuple[str, ...]


CHALLENGES: tuple[Challenge, ...] = (
    Challenge(
        id=1,
        slug="zombie-recipients",
        loop_dir="01-zombie-recipients",
        name="Zombie Recipients",
        status_default="RUNNABLE_WITH_EXTRA_MATERIALIZATION",
        artifact_type="review_lead",
        challenge_statement=(
            "Which companies and nonprofits received large amounts of public funding and then "
            "ceased operations shortly after?"
        ),
        ai_native_pattern=(
            "High government funding share plus stale CRA filing year, cross-checked against "
            "federal and Alberta funding exposure."
        ),
        direct_tables=(
            "cra.govt_funding_by_charity",
            "cra.cra_identification",
            "general.vw_entity_funding",
            "fed.grants_contributions",
            "ab.ab_grants",
        ),
        roadblocks=(
            "The current schema supports stale filing, not legal dissolution or bankruptcy.",
            "Legal status needs Corporations Canada or provincial registry evidence.",
        ),
        finding_challenges=(),
    ),
    Challenge(
        id=2,
        slug="ghost-capacity",
        loop_dir="02-ghost-capacity",
        name="Ghost Capacity",
        status_default="RUNNABLE_NOW",
        artifact_type="review_lead",
        challenge_statement=(
            "Which funded organizations show no evidence of actually being able to deliver what "
            "they were funded to do?"
        ),
        ai_native_pattern=(
            "Persistent government dependency combined with low program spend, high compensation "
            "pressure, and thin physical-capacity proxies."
        ),
        direct_tables=(
            "cra.govt_funding_by_charity",
            "cra.overhead_by_charity",
            "cra.cra_compensation",
            "cra.cra_identification",
        ),
        roadblocks=(
            "Employee counts and physical presence are partial proxies in the open data.",
            "Hospitals, school boards, and public authorities need explicit exclusions.",
        ),
        finding_challenges=(),
    ),
    Challenge(
        id=3,
        slug="funding-loops",
        loop_dir="03-funding-loops",
        name="Funding Loops",
        status_default="RUNNABLE_NOW",
        artifact_type="finding",
        challenge_statement="Where does money flow in circles between charities, and does it matter?",
        ai_native_pattern=(
            "CRA's precomputed circular-gift graph plus financial and governance context to "
            "separate normal federated structures from review leads."
        ),
        direct_tables=(
            "cra.loop_universe",
            "cra.loop_edges",
            "cra.loop_participants",
            "cra.johnson_cycles",
            "cra.overhead_by_charity",
        ),
        roadblocks=(
            "Denominational and federated charity structures can be legitimate circular flow.",
        ),
        finding_challenges=("funding_loops",),
    ),
    Challenge(
        id=4,
        slug="sole-source-amendment",
        loop_dir="04-sole-source-amendment",
        name="Sole Source And Amendment Creep",
        status_default="RUNNABLE_WITH_EXTRA_MATERIALIZATION",
        artifact_type="finding",
        challenge_statement=(
            "Which contracts started small and competitive but grew large through sole-source "
            "amendments?"
        ),
        ai_native_pattern=(
            "Latest federal agreement value compared with original value, plus Alberta "
            "sole-source dominance and same-vendor follow-on patterns."
        ),
        direct_tables=("fed.grants_contributions", "ab.ab_sole_source", "ab.ab_contracts"),
        roadblocks=(
            "Federal procurement contract data is not the same as federal grants and contributions.",
            "Bidder count, losing bids, and complete procurement method history need extra data.",
        ),
        finding_challenges=("amendment_creep", "sole_source_concentration"),
    ),
    Challenge(
        id=5,
        slug="vendor-concentration",
        loop_dir="05-vendor-concentration",
        name="Vendor Concentration",
        status_default="RUNNABLE_NOW",
        artifact_type="finding",
        challenge_statement="In any given category of government spending, how many vendors are actually competing?",
        ai_native_pattern=(
            "HHI and top-vendor share by ministry, program, service, and year, with statutory "
            "monopoly caveats."
        ),
        direct_tables=("fed.grants_contributions", "ab.ab_sole_source", "ab.ab_contracts"),
        roadblocks=(
            "Concentration can be deliberate program design or statutory monopoly, not necessarily drift.",
        ),
        finding_challenges=("vendor_concentration", "sole_source_concentration"),
    ),
    Challenge(
        id=6,
        slug="related-parties",
        loop_dir="06-related-parties",
        name="Related Parties And Governance Networks",
        status_default="RUNNABLE_WITH_EXTRA_MATERIALIZATION",
        artifact_type="review_lead",
        challenge_statement="Who controls the entities that receive public money, and do they also control each other?",
        ai_native_pattern=(
            "CRA director names, qualified-donee transfers, golden records, and funding exposure "
            "joined into cautious name-overlap leads."
        ),
        direct_tables=(
            "cra.cra_directors",
            "cra.cra_qualified_donees",
            "general.entity_golden_records",
            "general.vw_entity_funding",
        ),
        roadblocks=(
            "Name-only director matches require identity validation before any control claim.",
            "Corporate registry principals and former public servant data are external.",
        ),
        finding_challenges=("related_parties",),
    ),
    Challenge(
        id=7,
        slug="policy-misalignment",
        loop_dir="07-policy-misalignment",
        name="Policy Misalignment",
        status_default="NEEDS_EXTERNAL_DATA",
        artifact_type="blocked_missing_data",
        challenge_statement="Is the money going where the government says its priorities are?",
        ai_native_pattern=(
            "Policy commitment text converted into measurable targets, then compared against "
            "actual funding flows."
        ),
        direct_tables=("fed.grants_contributions", "ab.ab_grants", "general.vw_entity_funding"),
        roadblocks=(
            "Policy texts, mandate letters, budget commitments, and target definitions are not in the database.",
        ),
        finding_challenges=(),
    ),
    Challenge(
        id=8,
        slug="duplicative-funding",
        loop_dir="08-duplicative-funding",
        name="Duplicative Funding And Funding Gaps",
        status_default="NEEDS_EXTERNAL_DATA",
        artifact_type="partial_finding",
        challenge_statement=(
            "Which organizations are being funded by multiple levels of government for the same "
            "purpose, and where are the gaps?"
        ),
        ai_native_pattern=(
            "Golden records surface cross-jurisdiction overlap; purpose and period comparison "
            "separate duplication from coordinated cofunding."
        ),
        direct_tables=(
            "general.vw_entity_funding",
            "general.entity_golden_records",
            "fed.grants_contributions",
            "ab.ab_grants",
        ),
        roadblocks=(
            "Overlap is runnable now; same-purpose duplication needs purpose and eligible-cost comparison.",
            "Funding gaps need an external policy-priority corpus.",
        ),
        finding_challenges=("tri_jurisdictional_funding",),
    ),
    Challenge(
        id=9,
        slug="contract-intelligence",
        loop_dir="09-contract-intelligence",
        name="Contract Intelligence",
        status_default="RUNNABLE_WITH_EXTRA_MATERIALIZATION",
        artifact_type="operating_insight",
        challenge_statement="What is Canada actually buying, and is it paying more over time?",
        ai_native_pattern=(
            "Spend growth decomposed into agreement count, average agreement value, and vendor "
            "concentration over time."
        ),
        direct_tables=("fed.grants_contributions", "ab.ab_sole_source", "ab.ab_contracts", "ab.ab_grants"),
        roadblocks=(
            "True unit cost requires quantities, units, or deliverable counts.",
            "Inflation adjustment needs external deflators.",
        ),
        finding_challenges=(),
    ),
    Challenge(
        id=10,
        slug="adverse-media",
        loop_dir="10-adverse-media",
        name="Adverse Media",
        status_default="NEEDS_EXTERNAL_DATA",
        artifact_type="blocked_missing_data",
        challenge_statement="Which organizations receiving public funding are the subject of serious adverse media coverage?",
        ai_native_pattern=(
            "Externally cited regulatory, court, sanctions, and safety events matched back to funded entities."
        ),
        direct_tables=(
            "general.entity_golden_records",
            "general.entity_source_links",
            "fed.grants_contributions",
            "ab.ab_grants",
            "cra.t3010_impossibilities",
        ),
        roadblocks=(
            "The database does not contain adverse media.",
            "CRA arithmetic impossibilities are internal data-quality flags, not adverse media.",
        ),
        finding_challenges=(),
    ),
)


def by_id() -> dict[int, Challenge]:
    return {challenge.id: challenge for challenge in CHALLENGES}


def by_loop_dir() -> dict[str, Challenge]:
    return {challenge.loop_dir: challenge for challenge in CHALLENGES}
