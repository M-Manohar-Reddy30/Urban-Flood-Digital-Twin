
import csv
from pathlib import Path

OUTPUT = Path("data/processed/flood_mitigation_projects.csv")

SOURCE_DOCUMENT = (
    "Ballari District Disaster Management Plan 2025-26 & 2026-27"
)
SOURCE_URL = (
    "https://cdn.s3waas.gov.in/s37c590f01490190db0ed02a5070e20f01/"
    "uploads/2025/09/17573977807748.pdf"
)
SOURCE_PAGE = "259"

# Transcribed from the proposed mitigation projects table.
# These are proposals, not confirmed completed works or flood incidents.
projects = [
    {
        "record_id": "DDMP-MIT-001",
        "taluk": "Ballari",
        "location": "Government High School, Indira Nagar, Ward 35, Ballari city",
        "proposed_work": "Construction of stormwater drain",
        "proposed_cost_lakh": "20.00",
    },
    {
        "record_id": "DDMP-MIT-002",
        "taluk": "Ballari",
        "location": "Near Mllerpet Gaddekelage, Ward 13, Ballari city",
        "proposed_work": "Construction of stormwater drain",
        "proposed_cost_lakh": "50.00",
    },
    {
        "record_id": "DDMP-MIT-003",
        "taluk": "Ballari",
        "location": "Behind Bandimote Masjid, Ward 03, Ballari city",
        "proposed_work": "Construction of stormwater drain",
        "proposed_cost_lakh": "63.50",
    },
    {
        "record_id": "DDMP-MIT-004",
        "taluk": "Ballari",
        "location": (
            "Near Nagappa Katte to Heera Function Hall Road, "
            "Kanka Nagara, Bandihatti, Ward 32, Ballari city"
        ),
        "proposed_work": "Construction of stormwater drain",
        "proposed_cost_lakh": "40.00",
    },
    {
        "record_id": "DDMP-MIT-005",
        "taluk": "Ballari",
        "location": "D.C. Colony, Ward 8, Ballari city",
        "proposed_work": "Construction of stormwater drain",
        "proposed_cost_lakh": "80.00",
    },
    {
        "record_id": "DDMP-MIT-006",
        "taluk": "Ballari",
        "location": "Moka–B.D. Halli MDR, chainage 0.30 km, Ballari taluk",
        "proposed_work": "Construction of box culvert",
        "proposed_cost_lakh": "200.00",
    },
    {
        "record_id": "DDMP-MIT-007",
        "taluk": "Ballari",
        "location": "Moka–B.D. Halli MDR, chainage 0.45 km, Ballari taluk",
        "proposed_work": "Construction of box culvert",
        "proposed_cost_lakh": "150.00",
    },
    {
        "record_id": "DDMP-MIT-008",
        "taluk": "Kurugodu",
        "location": (
            "Chainage 38.60 km, Kampli–Kurugodu–Kudtini–"
            "Haraginadoni–Moka alur SH 132, Kampli"
        ),
        "proposed_work": "Construction of box culvert",
        "proposed_cost_lakh": "189.20",
    },
    {
        "record_id": "DDMP-MIT-009",
        "taluk": "Siruguppa",
        "location": (
            "Chainage 3.17 km on the Kududarahal–"
            "Nadanga–Vattamuruvani via Kottalachintha road"
        ),
        "proposed_work": (
            "Replace existing pipe culvert with "
            "a 1 m diameter Hume pipe culvert"
        ),
        "proposed_cost_lakh": "30.00",
    },
    {
        "record_id": "DDMP-MIT-010",
        "taluk": "Ballari",
        "location": "Vishal Nagar and Hanuman Nagar, Ward 17, Ballari city",
        "proposed_work": "Construction of stormwater drain",
        "proposed_cost_lakh": "31.83",
    },
]

fieldnames = [
    "record_id",
    "record_type",
    "taluk",
    "location",
    "proposed_work",
    "proposed_cost_lakh",
    "cost_unit",
    "project_status",
    "verification_status",
    "latitude",
    "longitude",
    "source_document",
    "source_page",
    "source_url",
    "notes",
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()

    for project in projects:
        writer.writerow(
            {
                **project,
                "record_type": "proposed_flood_mitigation_project",
                "cost_unit": "INR_lakh",
                "project_status": "proposed_in_source_document",
                "verification_status": "transcribed_not_independently_verified",
                "latitude": "",
                "longitude": "",
                "source_document": SOURCE_DOCUMENT,
                "source_page": SOURCE_PAGE,
                "source_url": SOURCE_URL,
                "notes": (
                    "Source describes a proposed mitigation project. "
                    "Completion, actual expenditure, exact coordinates, "
                    "and any historical flood incident at this location "
                    "have not been established by this record."
                ),
            }
        )

print(f"Saved {len(projects)} projects to {OUTPUT}")
print("Coordinates left blank; proposals are not flood-event labels.")
