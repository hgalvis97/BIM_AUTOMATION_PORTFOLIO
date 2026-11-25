
# -*- coding: utf-8 -*-

"""CSV export module for the BIM Quantity Extractor."""

import os
import csv
import codecs
import tempfile
import shutil

from datetime import datetime

# --------------------------------------------------
# 1. Export configuration
# --------------------------------------------------

QUANTITY_FIELDS = [
    "length_m",
    "area_m2",
    "volume_m3",
    "width_mm",
    "height_mm"
]

SUM_FIELDS = [
    "length_m",
    "area_m2",
    "volume_m3"
]

RANGE_FIELDS = [
    "width_mm",
    "height_mm"
]

# --------------------------------------------------
# 2. CSV formatting
# --------------------------------------------------

def format_csv_value(value):
    """Convert values into UTF-8 CSV-compatible strings."""

    if value is None:
        return ""

    if isinstance(value, (list, tuple)):
        value = "; ".join(
            unicode(item) for item in value
        )

    if isinstance(value, float):
        return "{:.15g}".format(value)

    if isinstance(value, unicode):
        return value.encode("utf-8")

    return str(value)

def write_csv(file_path, headers, records):
    """Write dictionaries to a UTF-8 CSV file."""

    with open(file_path, "wb") as csv_file:

        csv_file.write(codecs.BOM_UTF8)

        writer = csv.writer(csv_file)

        writer.writerow(headers)

        for record in records:

            row = [
                format_csv_value(record.get(field))
                for field in headers
            ]

            writer.writerow(row)

# --------------------------------------------------
# 3. Individual quantity status
# --------------------------------------------------

def get_element_quantity_status(record, field):

    if record["quantity_status"] == "UNSUPPORTED":
        return "EXCLUDED"

    if field not in record["required_fields"]:
        return "N/A"

    if record[field] is None:
        return "MISSING"

    return "OK"

# --------------------------------------------------
# 4. Prepare individual element dataset
# --------------------------------------------------

def prepare_element_dataset(records):

    headers = [
        "model_name",
        "element_id",
        "unique_id",
        "category",
        "family",
        "type_name",
        "type_id",
        "level",
        "level_id",
        "level_source",
        "level_status",
        "wall_kind",
        "count",
        "supported_count"
    ]

    for field in QUANTITY_FIELDS:

        headers.append(field)
        headers.append(field + "_status")

    headers.extend([
        "quantity_status",
        "required_fields",
        "missing_fields"
    ])

    rows = []

    for record in records:

        row = dict(record)

        if record["quantity_status"] == "UNSUPPORTED":
            row["supported_count"] = 0
        else:
            row["supported_count"] = 1

        for field in QUANTITY_FIELDS:

            row[field + "_status"] = (
                get_element_quantity_status(
                    record,
                    field
                )
            )

        rows.append(row)

    return headers, rows

# --------------------------------------------------
# 5. Aggregated quantity status
# --------------------------------------------------

def get_summary_status(summary):

    expected = summary["expected_count"]
    valid = summary["valid_count"]

    if expected == 0:
        return "N/A"

    if valid == 0:
        return "MISSING"

    if valid < expected:
        return "PARTIAL"

    return "OK"

# --------------------------------------------------
# 6. Prepare aggregated quantity dataset
# --------------------------------------------------

def prepare_aggregated_dataset(model_name, groups):

    headers = [
        "model_name",
        "group_id",
        "category",
        "level",
        "level_id",
        "family",
        "type_name",
        "type_id",
        "wall_kind",
        "count",
        "review_count"
    ]

    for field in SUM_FIELDS:

        headers.append(field)
        headers.append(field + "_status")
        headers.append(field + "_valid_count")
        headers.append(field + "_expected_count")

    for field in RANGE_FIELDS:

        headers.append(field + "_min")
        headers.append(field + "_max")
        headers.append(field + "_status")
        headers.append(field + "_valid_count")
        headers.append(field + "_expected_count")

    headers.append("element_ids")

    rows = []

    for index, group in enumerate(groups, 1):

        row = {
            "model_name": model_name,
            "group_id": index,
            "category": group["category"],
            "level": group["level"],
            "level_id": group["level_id"],
            "family": group["family"],
            "type_name": group["type_name"],
            "type_id": group["type_id"],
            "wall_kind": group["wall_kind"],
            "count": group["count"],
            "review_count": group["review_count"],
            "element_ids": group["element_ids"]
        }

        for field in SUM_FIELDS:

            summary = group["quantities"][field]

            row[field] = (
                summary["sum"]
                if summary["valid_count"] > 0
                else None
            )

            row[field + "_status"] = (
                get_summary_status(summary)
            )

            row[field + "_valid_count"] = (
                summary["valid_count"]
            )

            row[field + "_expected_count"] = (
                summary["expected_count"]
            )

        for field in RANGE_FIELDS:

            summary = group["quantities"][field]

            row[field + "_min"] = summary["min"]
            row[field + "_max"] = summary["max"]

            row[field + "_status"] = (
                get_summary_status(summary)
            )

            row[field + "_valid_count"] = (
                summary["valid_count"]
            )

            row[field + "_expected_count"] = (
                summary["expected_count"]
            )

        rows.append(row)

    return headers, rows

# --------------------------------------------------
# 7. Prepare validation dataset
# --------------------------------------------------

def prepare_validation_dataset(
        model_name, records, groups, selected_categories):

    headers = [
        "model_name",
        "check_type",
        "category",
        "quantity",
        "element_id",
        "raw_value",
        "grouped_value",
        "valid_count",
        "expected_count",
        "status",
        "details"
    ]

    rows = []

    # Count reconciliation.

    supported = [
        record for record in records
        if record["quantity_status"] != "UNSUPPORTED"
    ]

    grouped_count = sum(
        group["count"]
        for group in groups
    )

    unique_ids = set(
        record["element_id"]
        for record in records
    )

    rows.append({
        "check_type": "Count Reconciliation",
        "raw_value": len(supported),
        "grouped_value": grouped_count,
        "status": (
            "PASS"
            if len(supported) == grouped_count
            else "FAIL"
        ),
        "details": "Supported vs grouped instances"
    })

    rows.append({
        "check_type": "Unique Element IDs",
        "raw_value": len(records),
        "grouped_value": len(unique_ids),
        "status": (
            "PASS"
            if len(records) == len(unique_ids)
            else "FAIL"
        ),
        "details": "Collected vs unique element IDs"
    })

    # Category-level reconciliation.

    for category in selected_categories:

        category_records = [
            record for record in records
            if record["category"] == category
        ]

        category_supported = [
            record for record in category_records
            if record["quantity_status"] != "UNSUPPORTED"
        ]

        category_groups = [
            group for group in groups
            if group["category"] == category
        ]

        category_grouped = sum(
            group["count"]
            for group in category_groups
        )

        rows.append({
            "check_type": "Category Count",
            "category": category,
            "raw_value": len(category_supported),
            "grouped_value": category_grouped,
            "status": (
                "PASS"
                if len(category_supported) == category_grouped
                else "FAIL"
            ),
            "details": (
                "Collected: {}; Unsupported: {}".format(
                    len(category_records),
                    len(category_records)
                    - len(category_supported)
                )
            )
        })

        # Physical quantity reconciliation.

        for field in SUM_FIELDS:

            applicable = [
                record for record in category_supported
                if field in record["required_fields"]
            ]

            if not applicable:
                continue

            raw_values = [
                record[field]
                for record in applicable
                if record[field] is not None
            ]

            raw_total = sum(raw_values)

            group_total = sum(
                group["quantities"][field]["sum"]
                for group in category_groups
            )

            group_valid = sum(
                group["quantities"][field]["valid_count"]
                for group in category_groups
            )

            group_expected = sum(
                group["quantities"][field]["expected_count"]
                for group in category_groups
            )

            tolerance = max(
                0.000001,
                abs(raw_total) * 0.000000001
            )

            matches = (
                abs(raw_total - group_total) <= tolerance
                and len(raw_values) == group_valid
                and len(applicable) == group_expected
            )

            if not matches:
                status = "FAIL"

            elif not raw_values:
                status = "NO DATA"

            elif len(raw_values) < len(applicable):
                status = "PASS (Partial)"

            else:
                status = "PASS"

            rows.append({
                "check_type": "Quantity Reconciliation",
                "category": category,
                "quantity": field,
                "raw_value": (
                    raw_total if raw_values else None
                ),
                "grouped_value": (
                    group_total if group_valid else None
                ),
                "valid_count": len(raw_values),
                "expected_count": len(applicable),
                "status": status,
                "details": "Raw vs aggregated quantities"
            })

    # Individual validation findings.

    for record in records:

        if record["quantity_status"] == "REVIEW":

            rows.append({
                "check_type": "Missing Quantity",
                "category": record["category"],
                "element_id": record["element_id"],
                "status": "REVIEW",
                "details": record["missing_fields"]
            })

        if record["level_status"] == "UNRESOLVED":

            rows.append({
                "check_type": "Level Identification",
                "category": record["category"],
                "element_id": record["element_id"],
                "status": "REVIEW",
                "details": "No valid associated level"
            })

        if record["quantity_status"] == "UNSUPPORTED":

            rows.append({
                "check_type": "Unsupported Element",
                "category": record["category"],
                "element_id": record["element_id"],
                "status": "EXCLUDED",
                "details": record["type_name"]
            })

    for row in rows:
        row["model_name"] = model_name

    return headers, rows

# --------------------------------------------------
# 8. Export all datasets
# --------------------------------------------------

def export_datasets(
        parent_folder,
        model_name,
        records,
        groups,
        selected_categories):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    datasets = [
        (
            "element_quantities.csv",
            prepare_element_dataset(records)
        ),
        (
            "aggregated_quantities.csv",
            prepare_aggregated_dataset(
                model_name,
                groups
            )
        ),
        (
            "validation_report.csv",
            prepare_validation_dataset(
                model_name,
                records,
                groups,
                selected_categories
            )
        )
    ]

    export_folder = tempfile.mkdtemp(
        prefix="BIM_Quantities_" + timestamp + "_",
        dir=parent_folder
    )

    exported_files = []

    try:

        for filename, dataset in datasets:

            headers, rows = dataset

            file_path = os.path.join(
                export_folder,
                filename
            )

            write_csv(
                file_path,
                headers,
                rows
            )

            exported_files.append({
                "filename": filename,
                "path": file_path,
                "row_count": len(rows)
            })

    except Exception:

        # Remove incomplete export files.
        # Never delete previously existing exports.

        try:
            shutil.rmtree(export_folder)
        except Exception:
            pass

        raise

    return export_folder, exported_files