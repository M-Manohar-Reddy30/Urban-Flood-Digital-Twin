"""Build a clipped, auditable drainage line dataset for Ballari urban area.

Source geometries and classifications are preserved as source evidence.
This script does not establish that the network is complete or verified.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
SOURCE_KML = ROOT / "data/raw/drainage/ballari_drainage_source.kml"
BOUNDARY_FILE = ROOT / "data/processed/ballari_municipal_boundary.geojson"
OUTPUT_DIR = ROOT / "data/processed/drainage"
OUTPUT_GEOJSON = OUTPUT_DIR / "ballari_drainage_clipped.geojson"
OUTPUT_CSV = OUTPUT_DIR / "ballari_drainage_feature_audit.csv"
OUTPUT_REPORT = OUTPUT_DIR / "ballari_drainage_audit.md"

SOURCE_CRS = "EPSG:4326"
METRIC_CRS = "EPSG:32643"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def read_placemark_attributes(placemark: ET.Element) -> dict[str, str]:
    """Read KML SimpleData and Data/value attributes."""
    attrs: dict[str, str] = {}

    for element in placemark.iter():
        tag = local_name(element.tag)

        if tag == "SimpleData":
            key = element.attrib.get("name", "")
            if key:
                attrs[key] = (element.text or "").strip()

        elif tag == "Data":
            key = element.attrib.get("name", "")
            if not key:
                continue

            value = ""
            for child in element:
                if local_name(child.tag) == "value":
                    value = (child.text or "").strip()
                    break
            attrs[key] = value

    return attrs


def parse_coordinates(text: str) -> list[tuple[float, float]]:
    """Parse KML longitude,latitude[,altitude] coordinate tuples."""
    coordinates: list[tuple[float, float]] = []

    for token in text.split():
        parts = token.split(",")
        if len(parts) < 2:
            continue

        lon, lat = float(parts[0]), float(parts[1])

        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError(f"Invalid longitude/latitude: {token}")

        coordinates.append((lon, lat))

    return coordinates


def extract_line_parts(
    placemark: ET.Element,
) -> list[LineString]:
    """Extract individual LineStrings from a source placemark."""
    parts: list[LineString] = []

    for element in placemark.iter():
        if local_name(element.tag) != "LineString":
            continue

        coordinate_element = next(
            (
                child
                for child in element.iter()
                if local_name(child.tag) == "coordinates"
            ),
            None,
        )

        if coordinate_element is None or not coordinate_element.text:
            continue

        coordinates = parse_coordinates(coordinate_element.text)

        if len(coordinates) >= 2:
            line = LineString(coordinates)
            if not line.is_empty and line.is_valid and line.length > 0:
                parts.append(line)

    return parts


def read_source_network() -> gpd.GeoDataFrame:
    """Parse source placemarks, retaining source IDs and attributes."""
    root = ET.parse(SOURCE_KML).getroot()
    records: list[dict] = []

    for element in root.iter():
        if local_name(element.tag) != "Placemark":
            continue

        attrs = read_placemark_attributes(element)
        source_id = attrs.get("OBJECTID", "").strip()

        if not source_id:
            raise ValueError("Encountered a source placemark without OBJECTID")

        lines = extract_line_parts(element)

        # Preserve every placemark in the audit, including one with no
        # usable line parts, rather than silently dropping source records.
        if not lines:
            records.append(
                {
                    "source_id": source_id,
                    "category": attrs.get("category", "") or "Unknown",
                    "dr_code": attrs.get("dr_code", ""),
                    "status": attrs.get("status", ""),
                    "source_length_attribute": attrs.get(
                        "SHAPE.STLength()", ""
                    ),
                    "source_line_part_count": 0,
                    "geometry": None,
                }
            )
            continue

        records.append(
            {
                "source_id": source_id,
                "category": attrs.get("category", "") or "Unknown",
                "dr_code": attrs.get("dr_code", ""),
                "status": attrs.get("status", ""),
                "source_length_attribute": attrs.get(
                    "SHAPE.STLength()", ""
                ),
                "source_line_part_count": len(lines),
                "geometry": MultiLineString(lines) if len(lines) > 1 else lines[0],
            }
        )

    ids = [record["source_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate OBJECTID values found in source KML")

    return gpd.GeoDataFrame(records, geometry="geometry", crs=SOURCE_CRS)


def main() -> None:
    for required in (SOURCE_KML, BOUNDARY_FILE):
        if not required.exists():
            raise FileNotFoundError(f"Required input not found: {required}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Prevent stale spatial output if a rerun produces no clipped features.
    OUTPUT_GEOJSON.unlink(missing_ok=True)

    source = read_source_network()
    boundary = gpd.read_file(BOUNDARY_FILE)

    if boundary.empty:
        raise ValueError("Municipal boundary contains no features")

    if boundary.crs is None:
        raise ValueError("Municipal boundary CRS is missing")

    boundary = boundary.to_crs(SOURCE_CRS)
    city_geometry = unary_union(
        [geom for geom in boundary.geometry if geom is not None and not geom.is_empty]
    )

    if city_geometry.is_empty or not city_geometry.is_valid:
        raise ValueError("Municipal boundary geometry is empty or invalid")

    # Perform clipping in a projected CRS using consistent 2D geometries.
    boundary_metric = boundary.to_crs(METRIC_CRS)
    boundary_metric.geometry = boundary_metric.geometry.force_2d()
    city_metric = unary_union(
        [geom for geom in boundary_metric.geometry
         if geom is not None and not geom.is_empty]
    )

    if city_metric.is_empty or not city_metric.is_valid:
        raise ValueError("Projected municipal boundary is empty or invalid")

    valid_source = source[
        source.geometry.notna() & ~source.geometry.is_empty
    ].copy()
    source_metric = valid_source.to_crs(METRIC_CRS)
    source_metric.geometry = source_metric.geometry.force_2d()

    valid_source["intersects_city"] = (
        source_metric.geometry.intersects(city_metric).values
    )
    valid_source["within_city"] = (
        source_metric.geometry.within(city_metric).values
    )

    clipped_geometries = source_metric.geometry.intersection(city_metric)

    clipped_records: list[dict] = []
    for (_, row), clipped_geometry in zip(
        valid_source.iterrows(), clipped_geometries
    ):
        if clipped_geometry.is_empty:
            continue

        # Keep only line components from a potentially mixed intersection.
        line_parts: list[LineString] = []

        def collect_lines(geom) -> None:
            if geom.geom_type == "LineString":
                if geom.length > 0:
                    line_parts.append(geom)
            elif geom.geom_type in {"MultiLineString", "GeometryCollection"}:
                for child in geom.geoms:
                    collect_lines(child)

        collect_lines(clipped_geometry)

        if not line_parts:
            continue

        final_geometry = (
            MultiLineString(line_parts) if len(line_parts) > 1 else line_parts[0]
        )

        clipped_records.append(
            {
                "source_id": row["source_id"],
                "category": row["category"],
                "dr_code": row["dr_code"],
                "status": row["status"],
                "source_length_attribute": row["source_length_attribute"],
                "source_line_part_count": int(row["source_line_part_count"]),
                "intersects_city": bool(row["intersects_city"]),
                "within_city": bool(row["within_city"]),
                "clipped_line_part_count": len(line_parts),
                "geometry": final_geometry,
            }
        )

    clipped = gpd.GeoDataFrame(
        clipped_records,
        geometry="geometry",
        crs=METRIC_CRS,
    ).to_crs(SOURCE_CRS)

    if not clipped.empty:
        clipped_metric = clipped.to_crs(METRIC_CRS)
        clipped["clipped_length_m"] = clipped_metric.geometry.length.values
        clipped["clipped_length_km"] = clipped["clipped_length_m"] / 1000
        clipped["metric_crs_for_length"] = METRIC_CRS
        clipped.to_file(OUTPUT_GEOJSON, driver="GeoJSON")

    # Source-level audit: exactly one row per source OBJECTID.
    source_audit = source.drop(columns="geometry").copy()
    source_audit["source_length_attribute"] = pd.to_numeric(
        source_audit["source_length_attribute"], errors="coerce"
    )
    source_audit["intersects_city"] = False
    source_audit["within_city"] = False
    source_audit["clipped_length_km"] = 0.0
    source_audit["clipped_line_part_count"] = 0

    source_spatial = valid_source.set_index("source_id")
    for idx, row in source_audit.iterrows():
        sid = row["source_id"]
        if sid in source_spatial.index:
            source_audit.at[idx, "intersects_city"] = bool(
                source_spatial.at[sid, "intersects_city"]
            )
            source_audit.at[idx, "within_city"] = bool(
                source_spatial.at[sid, "within_city"]
            )

    if not clipped.empty:
        by_source = clipped.groupby("source_id").agg(
            clipped_length_km=("clipped_length_km", "sum"),
            clipped_line_part_count=("clipped_line_part_count", "sum"),
        )
        for idx, row in source_audit.iterrows():
            sid = row["source_id"]
            if sid in by_source.index:
                source_audit.at[idx, "clipped_length_km"] = float(
                    by_source.at[sid, "clipped_length_km"]
                )
                source_audit.at[idx, "clipped_line_part_count"] = int(
                    by_source.at[sid, "clipped_line_part_count"]
                )

    source_audit.to_csv(OUTPUT_CSV, index=False)

    category_source_counts = source["category"].value_counts().to_dict()
    category_intersections = (
        source_audit[source_audit["intersects_city"]]["category"]
        .value_counts()
        .to_dict()
    )
    category_clipped_length = (
        clipped.groupby("category")["clipped_length_km"].sum().to_dict()
        if not clipped.empty
        else {}
    )

    report_lines = [
        "# Ballari Drainage Network Audit",
        "",
        "## Source",
        "",
        f"- Input: `{SOURCE_KML.relative_to(ROOT)}`",
        f"- Boundary: `{BOUNDARY_FILE.relative_to(ROOT)}`",
        "- Source CRS: EPSG:4326 (KML longitude/latitude)",
        f"- Metric CRS for lengths: {METRIC_CRS}",
        "- Source attribution: KSRSAC, distributed through OpenCity.",
        "- Resource license metadata: Public Domain; retain source attribution.",
        "",
        "## Processing results",
        "",
        f"- Source placemarks: {len(source):,}",
        f"- Unique source IDs: {source['source_id'].nunique():,}",
        f"- Source placemarks with usable line geometry: {len(valid_source):,}",
        f"- Source placemarks intersecting the municipal boundary: "
        f"{int(source_audit['intersects_city'].sum()):,}",
        f"- Source placemarks entirely within the boundary: "
        f"{int(source_audit['within_city'].sum()):,}",
        f"- Clipped output records: {len(clipped):,}",
        f"- Total clipped line length: "
        f"{clipped['clipped_length_km'].sum() if not clipped.empty else 0:.3f} km",
        "",
        "### Source placemarks by category",
        "",
    ]

    report_lines.extend(
        f"- {category}: {count:,}"
        for category, count in sorted(category_source_counts.items())
    )

    report_lines.extend(["", "### Intersecting source placemarks by category", ""])
    report_lines.extend(
        f"- {category}: {count:,}"
        for category, count in sorted(category_intersections.items())
    )

    report_lines.extend(["", "### Clipped line length by category", ""])
    report_lines.extend(
        f"- {category}: {length:.3f} km"
        for category, length in sorted(category_clipped_length.items())
    )

    report_lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- Clipped GeoJSON: `{OUTPUT_GEOJSON.relative_to(ROOT)}`",
            f"- Source-level CSV audit: `{OUTPUT_CSV.relative_to(ROOT)}`",
            "",
            "## Limitations",
            "",
            "- Categories are copied from the source; their detailed definitions "
            "and positional accuracy have not been independently verified.",
            "- The `Drain` category is not assumed to mean exclusively "
            "engineered stormwater drains.",
            "- Source linework is not assumed to be complete or current.",
            "- Blank status values are not interpreted as an operational condition.",
            "- Intersecting features and clipped lengths describe mapped geometry, "
            "not verified infrastructure or flood occurrence.",
            "- This layer is not a flood-risk score, validated prediction, or "
            "ground-truth label dataset.",
            "",
        ]
    )

    OUTPUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    print("Drainage processing complete.")
    print("Source placemarks:", len(source))
    print("Unique source IDs:", source["source_id"].nunique())
    print("Source categories:", json.dumps(category_source_counts, sort_keys=True))
    print("Intersecting source placemarks:",
          int(source_audit["intersects_city"].sum()))
    print("Entirely within city:",
          int(source_audit["within_city"].sum()))
    print("Clipped output records:", len(clipped))
    print("Clipped length (km):",
          round(clipped["clipped_length_km"].sum(), 3)
          if not clipped.empty else 0)
    print("GeoJSON:", OUTPUT_GEOJSON.relative_to(ROOT))
    print("CSV:", OUTPUT_CSV.relative_to(ROOT))
    print("Report:", OUTPUT_REPORT.relative_to(ROOT))


if __name__ == "__main__":
    main()
