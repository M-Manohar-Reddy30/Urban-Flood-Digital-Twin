import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_FILE = PROJECT_ROOT / "data" / "processed" / "flood_evidence_inventory.csv"


def get_evidence_summary() -> dict:
    if not EVIDENCE_FILE.exists():
        raise FileNotFoundError("Flood evidence inventory was not found.")

    with EVIDENCE_FILE.open("r", encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))

    return {
        "total_records": len(records),
        "record_types": _count_by(records, "record_type"),
        "verification_statuses": _count_by(
            records, "verification_status"
        ),
        "spatial_verification_statuses": _count_by(
            records, "spatial_verification_status"
        ),
        "records": records,
        "note": (
            "Reported evidence only. These records are not validated "
            "flood-model training labels or predictions."
        ),
    }


def _count_by(records: list[dict], field: str) -> dict:
    counts = {}
    for record in records:
        value = record.get(field) or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts
