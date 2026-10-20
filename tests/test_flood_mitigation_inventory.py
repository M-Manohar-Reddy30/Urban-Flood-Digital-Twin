
import csv
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "data" / "processed" / "flood_mitigation_projects.csv"
BUILDER = PROJECT_ROOT / "scripts" / "build_flood_mitigation_inventory.py"


def load_projects():
    with OUTPUT.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_builder_recreates_mitigation_inventory():
    result = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Saved 10 projects" in result.stdout
    assert OUTPUT.is_file()


def test_mitigation_inventory_has_ten_unique_records():
    records = load_projects()

    assert len(records) == 10
    assert len({record["record_id"] for record in records}) == 10


def test_proposed_cost_total_matches_transcribed_values():
    records = load_projects()

    total = sum(
        (Decimal(record["proposed_cost_lakh"]) for record in records),
        Decimal("0"),
    )

    assert total == Decimal("854.53")


def test_proposals_are_not_flood_event_labels():
    records = load_projects()

    assert all(
        record["record_type"] == "proposed_flood_mitigation_project"
        for record in records
    )
    assert all(
        record["project_status"] == "proposed_in_source_document"
        for record in records
    )


def test_coordinates_remain_blank_until_verified():
    records = load_projects()

    assert all(
        not record["latitude"] and not record["longitude"]
        for record in records
    )


def test_records_preserve_source_and_verification_status():
    records = load_projects()

    assert all(record["source_url"].startswith("https://") for record in records)
    assert all(record["source_page"] == "259" for record in records)
    assert all(
        record["verification_status"] == "transcribed_not_independently_verified"
        for record in records
    )
    assert all(record["proposed_cost_lakh"] for record in records)
