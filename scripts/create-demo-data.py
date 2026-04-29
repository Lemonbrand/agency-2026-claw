#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    write_csv(
        RAW / "contracts_demo.csv",
        [
            {"contract_id": "C-1001", "department": "Health", "category": "IT Services", "vendor_name": "Northstar Analytics", "original_value": 48000, "current_value": 231000, "director_name": "Avery Chen"},
            {"contract_id": "C-1002", "department": "Health", "category": "IT Services", "vendor_name": "Northstar Analytics", "original_value": 72000, "current_value": 76000, "director_name": "Avery Chen"},
            {"contract_id": "C-1003", "department": "Health", "category": "IT Services", "vendor_name": "Northstar Analytics", "original_value": 61000, "current_value": 65000, "director_name": "Avery Chen"},
            {"contract_id": "C-1004", "department": "Health", "category": "IT Services", "vendor_name": "Maple Systems", "original_value": 42000, "current_value": 43000, "director_name": "Maya Roy"},
            {"contract_id": "C-2001", "department": "Housing", "category": "Facilities", "vendor_name": "Civic Build Co", "original_value": 97000, "current_value": 112000, "director_name": "Olivier Tremblay"},
            {"contract_id": "C-2002", "department": "Housing", "category": "Facilities", "vendor_name": "Civic Build Co", "original_value": 30000, "current_value": 180000, "director_name": "Olivier Tremblay"},
            {"contract_id": "C-2003", "department": "Housing", "category": "Facilities", "vendor_name": "Ottawa Works", "original_value": 85000, "current_value": 88000, "director_name": "Samira Khan"},
        ],
    )
    write_csv(
        RAW / "charities_demo.csv",
        [
            {"charity_id": "CH-1", "recipient_name": "Northstar Community Fund", "director_name": "Avery Chen", "government_revenue": 2100000, "employees": 2, "program_spend": 180000},
            {"charity_id": "CH-2", "recipient_name": "Civic Housing Trust", "director_name": "Olivier Tremblay", "government_revenue": 1200000, "employees": 4, "program_spend": 930000},
            {"charity_id": "CH-3", "recipient_name": "Maple Youth Network", "director_name": "Maya Roy", "government_revenue": 620000, "employees": 9, "program_spend": 480000},
        ],
    )
    print(f"demo data written to {RAW}")


if __name__ == "__main__":
    main()
