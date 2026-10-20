from pathlib import Path

import pandas as pd


INVENTORY = Path("data/processed/flood_evidence_inventory.csv")


def load_inventory():
    assert INVENTORY.exists(), "Run the inventory generator first."
    return pd.read_csv(INVENTORY).set_index("record_id")


def test_vulnerable_village_population_values_are_preserved():
    df = load_inventory()

    assert df.loc["DDMP-2025-001", "location"] == "Moka"
    assert int(df.loc["DDMP-2025-001", "value"]) == 14600
    assert df.loc["DDMP-2025-001", "verification_status"] == (
        "table_column_alignment_verified"
    )

    assert df.loc["DDMP-2025-002", "location"] == "Kampli"
    assert int(df.loc["DDMP-2025-002", "value"]) == 53709
    assert df.loc["DDMP-2025-002", "verification_status"] == (
        "table_column_alignment_verified"
    )


def test_candidate_landmarks_do_not_become_incident_coordinates():
    df = load_inventory()

    for record_id in ["DH-2026-001", "DH-2026-002", "DH-2026-003"]:
        assert pd.isna(df.loc[record_id, "latitude"])
        assert pd.isna(df.loc[record_id, "longitude"])

    assert float(df.loc["DH-2026-001", "landmark_latitude"]) == 15.137672
    assert float(df.loc["DH-2026-001", "landmark_longitude"]) == 76.929557

    assert float(df.loc["DH-2026-003", "landmark_latitude"]) == 15.155818
    assert float(df.loc["DH-2026-003", "landmark_longitude"]) == 76.898437


def test_candidate_landmarks_have_caveated_status_and_source():
    df = load_inventory()

    for record_id in ["DH-2026-001", "DH-2026-003"]:
        assert df.loc[record_id, "landmark_spatial_status"] == (
            "candidate_landmark_inside_boundary_incident_location_unverified"
        )
        source = df.loc[record_id, "landmark_coordinate_source"]
        assert isinstance(source, str) and source.strip()

    assert df.loc["DH-2026-002", "landmark_spatial_status"] == "not_checked"
    assert pd.isna(df.loc["DH-2026-002", "landmark_latitude"])


def test_all_three_incidents_remain_in_inventory():
    df = load_inventory()
    for record_id in ["DH-2026-001", "DH-2026-002", "DH-2026-003"]:
        assert record_id in df.index
        assert df.loc[record_id, "source_url"].startswith("https://")
