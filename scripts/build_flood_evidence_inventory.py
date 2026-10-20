
import csv
from pathlib import Path

OUTPUT = Path("data/processed/flood_evidence_inventory.csv")

# Preliminary entries transcribed from the Ballari District
# Disaster Management Plan 2025-26 & 2026-27.
# These are district-level records, not confirmed city-level labels.

records = [
    {
        "record_id": "DDMP-2024-001",
        "record_type": "reported_flood_impact",
        "year": "2024",
        "location": "Moka",
        "taluk": "Ballari",
        "description": "Power substation reported waterlogged",
        "value": "",
        "unit": "",
        "geographic_scope": "district",
        "source_document": "Ballari District Disaster Management Plan 2025-26 & 2026-27",
        "source_section": "District past flood assessment and analysis",
        "source_page": "45",
        "verification_status": "transcribed_not_independently_verified",
        "notes": "Confirm location coordinates and whether it lies inside the city boundary.",
    },
    {
        "record_id": "DDMP-2024-002",
        "record_type": "reported_flood_impact",
        "year": "2024",
        "location": "Kurugodu",
        "taluk": "Kurugodu",
        "description": "School reported waterlogged",
        "value": "",
        "unit": "",
        "geographic_scope": "district",
        "source_document": "Ballari District Disaster Management Plan 2025-26 & 2026-27",
        "source_section": "District past flood assessment and analysis",
        "source_page": "45",
        "verification_status": "transcribed_not_independently_verified",
        "notes": "Outside the city model unless verified otherwise.",
    },
    {
        "record_id": "DDMP-2024-003",
        "record_type": "reported_flood_impact",
        "year": "2024",
        "location": "Kampli",
        "taluk": "Kampli",
        "description": "Bridge damage reported",
        "value": "",
        "unit": "",
        "geographic_scope": "district",
        "source_document": "Ballari District Disaster Management Plan 2025-26 & 2026-27",
        "source_section": "District past flood assessment and analysis",
        "source_page": "45",
        "verification_status": "transcribed_not_independently_verified",
        "notes": "Do not use as a Ballari city flood label.",
    },
    {
        "record_id": "DDMP-2024-004",
        "record_type": "reported_flood_impact",
        "year": "2024",
        "location": "Ballari taluk",
        "taluk": "Ballari",
        "description": "House damage attributed to heavy rainfall",
        "value": "",
        "unit": "",
        "geographic_scope": "district",
        "source_document": "Ballari District Disaster Management Plan 2025-26 & 2026-27",
        "source_section": "District past flood assessment and analysis",
        "source_page": "45",
        "verification_status": "location_requires_verification",
        "notes": "The report does not provide exact coordinates in the extracted caption.",
    },
    {
        "record_id": "DDMP-2025-001",
        "record_type": "reported_vulnerable_location",
        "year": "2025-26",
        "location": "Moka",
        "taluk": "Ballari",
        "description": "Listed in flood-vulnerable village table",
        "value": "14600",
        "unit": "reported_population",
        "geographic_scope": "district",
        "source_document": "Ballari District Disaster Management Plan 2025-26 & 2026-27",
        "source_section": "Table 2.10: vulnerable villages and population",
        "source_page": "47",
        "verification_status": "table_column_alignment_verified",
        "notes": "Value transcribed from the village population column in Table 2.10. Source table reports flood-vulnerable villages; this value is not a flood-affected population count or a verified Ballari city statistic. Underlying source figures have not been independently validated.",
    },
    {
        "record_id": "DDMP-2025-002",
        "record_type": "reported_vulnerable_location",
        "year": "2025-26",
        "location": "Kampli",
        "taluk": "Kampli",
        "description": "Listed in flood-vulnerable village table",
        "value": "53709",
        "unit": "reported_population",
        "geographic_scope": "district",
        "source_document": "Ballari District Disaster Management Plan 2025-26 & 2026-27",
        "source_section": "Table 2.10: vulnerable villages and population",
        "source_page": "47",
        "verification_status": "table_column_alignment_verified",
        "notes": "Value transcribed from the village population column in Table 2.10. Source table reports flood-vulnerable villages; this value is not a flood-affected population count or a verified Ballari city statistic. Underlying source figures have not been independently validated.",
    },

    {
        "record_id": "DH-2026-001",
        "record_type": "reported_flood_impact",
        "year": "2026-06-07",
        "location": "Kolmi Chowk, Ballari",
        "taluk": "Ballari",
        "description": "Flooded area photographed and identified in the article caption",
        "value": "",
        "unit": "",
        "geographic_scope": "city_reported",
        "source_document": "Deccan Herald: Rain exposes civic body's shoddy infra in Ballari",
        "source_section": "Article text and Kolmi Chowk photo caption",
        "source_page": "web article",
        "verification_status": "reported_location_coordinates_pending",
        "notes": "Article published 2026-06-08; incident described as occurring on June 7, 2026. Exact coordinates not verified.",
    },
    {
        "record_id": "DH-2026-002",
        "record_type": "reported_flood_impact",
        "year": "2026-06-07",
        "location": "Underpass near Kanaka Durgamma Temple, Ballari",
        "taluk": "Ballari",
        "description": "Rainwater reportedly stagnated at the underpass",
        "value": "",
        "unit": "",
        "geographic_scope": "city_reported",
        "source_document": "Deccan Herald: Rain exposes civic body's shoddy infra in Ballari",
        "source_section": "Article body",
        "source_page": "web article",
        "verification_status": "reported_location_coordinates_pending",
        "notes": "Exact underpass coordinates and municipal-boundary inclusion require verification.",
    },
    {
        "record_id": "DH-2026-003",
        "record_type": "reported_flood_impact",
        "year": "2026-06-07",
        "location": "VIMS hospital, Ballari",
        "taluk": "Ballari",
        "description": "Several hospital wards reportedly flooded",
        "value": "",
        "unit": "",
        "geographic_scope": "city_reported",
        "source_document": "Deccan Herald: Rain exposes civic body's shoddy infra in Ballari",
        "source_section": "Article body",
        "source_page": "web article",
        "verification_status": "reported_location_coordinates_pending",
        "notes": "Hospital campus coordinates and municipal-boundary inclusion require verification.",
    },
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# Preserve direct source traceability.
DDMP_URL = "https://cdn.s3waas.gov.in/s37c590f01490190db0ed02a5070e20f01/uploads/2025/09/17573977807748.pdf"
DECCAN_HERALD_URL = "https://www.deccanherald.com/india/karnataka/rain-exposes-civic-body-s-shoddy-infra-in-ballari-4030856"

for record in records:
    if record["source_document"].startswith("Ballari District Disaster"):
        record["source_url"] = DDMP_URL
    else:
        record["source_url"] = DECCAN_HERALD_URL

# Keep incident coordinates separate from landmark coordinates.
for record in records:
    record["latitude"] = ""
    record["longitude"] = ""
    record["inside_city_boundary"] = "not_checked"
    record["spatial_verification_status"] = "missing_incident_coordinates"

    record["landmark_latitude"] = ""
    record["landmark_longitude"] = ""
    record["landmark_coordinate_source"] = ""
    record["landmark_spatial_status"] = "not_checked"

# Candidate landmark coordinates only; never treat these as floodwater points.
for record in records:
    if record["record_id"] == "DH-2026-001":
        record["landmark_latitude"] = "15.137672"
        record["landmark_longitude"] = "76.929557"
        record["landmark_coordinate_source"] = (
            "Mappls listing for Sharada Tutorials at Kolmi Chowk; "
            "candidate coordinates; exact listing URL not yet verified"
        )
        record["landmark_spatial_status"] = (
            "candidate_landmark_inside_boundary_incident_location_unverified"
        )

    elif record["record_id"] == "DH-2026-003":
        record["landmark_latitude"] = "15.155818"
        record["landmark_longitude"] = "76.898437"
        record["landmark_coordinate_source"] = (
            "LatLong listing for Vijayanagar Institute of Medical Science "
            "Hospital, Ballari; candidate landmark; exact point not "
            "independently confirmed"
        )
        record["landmark_spatial_status"] = (
            "candidate_landmark_inside_boundary_incident_location_unverified"
        )

fieldnames = list(records[0].keys())

with OUTPUT.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

print(f"Saved {len(records)} records to {OUTPUT}")
print("Coordinate fields added; no coordinates have been invented.")
print("Status: spatial verification pending.")
