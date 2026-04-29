#!/usr/bin/env python3
from pathlib import Path

REPLACEMENTS = {
    "`fed.vw_agreement_current` does not exist": "no prebuilt current-agreement view exists",
    "as `fed.vw_agreement_current` does not exist": "because no prebuilt current-agreement view exists",
    "`cra.t3010_schedule6` is not available in the verified schema": "T3010 Schedule 6 charitable program descriptions are not available in the verified schema",
    "`general.entity_golden_records.entity_id`": "`general.entity_golden_records.id`",
    "general.entity_golden_records.entity_id": "general.entity_golden_records.id",
    "gr.entity_id = ef.entity_id": "gr.id = ef.entity_id",
    "`sha256: a1b2c3d4...`": "the SHA-256 hash of the replay SQL recorded by the runner",
}


def main() -> None:
    for brief in sorted(Path(".").glob("[0-9][0-9]-*/research-brief.md")):
        text = brief.read_text()
        old = text
        for src, dst in REPLACEMENTS.items():
            text = text.replace(src, dst)
        if text != old:
            brief.write_text(text)
            print(f"patched {brief}")


if __name__ == "__main__":
    main()
