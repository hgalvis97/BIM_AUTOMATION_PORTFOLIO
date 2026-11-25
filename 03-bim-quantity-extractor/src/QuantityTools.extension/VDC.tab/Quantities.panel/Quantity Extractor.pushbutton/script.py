
# -*- coding: utf-8 -*-

"""BIM Quantity Extractor - Validation and Aggregation."""

import math
import os
import sys

from pyrevit import revit, DB, forms, script

# Make the local export module available.

bundle_folder = os.path.dirname(__file__)

if bundle_folder not in sys.path:
    sys.path.insert(0, bundle_folder)

from quantity_export import export_datasets


doc = revit.doc
output = script.get_output()


# --------------------------------------------------
# 1. Quantity configuration
# --------------------------------------------------

QUANTITY_CONFIG = {
    "length_m": {
        "parameter": DB.BuiltInParameter.CURVE_ELEM_LENGTH,
        "unit": DB.UnitTypeId.Meters,
        "aggregation": "SUM",
        "label": "Length (m)"
    },
    "area_m2": {
        "parameter": DB.BuiltInParameter.HOST_AREA_COMPUTED,
        "unit": DB.UnitTypeId.SquareMeters,
        "aggregation": "SUM",
        "label": "Area (m2)"
    },
    "volume_m3": {
        "parameter": DB.BuiltInParameter.HOST_VOLUME_COMPUTED,
        "unit": DB.UnitTypeId.CubicMeters,
        "aggregation": "SUM",
        "label": "Volume (m3)"
    },
    "width_mm": {
        "parameter": DB.BuiltInParameter.FAMILY_WIDTH_PARAM,
        "unit": DB.UnitTypeId.Millimeters,
        "aggregation": "RANGE",
        "label": "Width (mm)"
    },
    "height_mm": {
        "parameter": DB.BuiltInParameter.FAMILY_HEIGHT_PARAM,
        "unit": DB.UnitTypeId.Millimeters,
        "aggregation": "RANGE",
        "label": "Height (mm)"
    }
}


# --------------------------------------------------
# 2. Category configuration
# --------------------------------------------------

CATEGORY_CONFIG = {
    "Walls": {
        "category": DB.BuiltInCategory.OST_Walls,
        "quantities": ["length_m", "area_m2", "volume_m3"]
    },
    "Floors": {
        "category": DB.BuiltInCategory.OST_Floors,
        "quantities": ["area_m2", "volume_m3"]
    },
    "Doors": {
        "category": DB.BuiltInCategory.OST_Doors,
        "quantities": ["width_mm", "height_mm"]
    },
    "Windows": {
        "category": DB.BuiltInCategory.OST_Windows,
        "quantities": ["width_mm", "height_mm"]
    },
    "Structural Columns": {
        "category": DB.BuiltInCategory.OST_StructuralColumns,
        "quantities": ["volume_m3"]
    }
}

CATEGORY_ORDER = [
    "Walls",
    "Floors",
    "Doors",
    "Windows",
    "Structural Columns"
]


# --------------------------------------------------
# 3. Level configuration
# --------------------------------------------------

LEVEL_CONFIG = {
    "Walls": [
        ("WALL_BASE_CONSTRAINT", "Base Constraint")
    ],
    "Floors": [
        ("LEVEL_PARAM", "Level Parameter")
    ],
    "Doors": [
        ("FAMILY_LEVEL_PARAM", "Family Level"),
        ("INSTANCE_REFERENCE_LEVEL_PARAM", "Reference Level")
    ],
    "Windows": [
        ("FAMILY_LEVEL_PARAM", "Family Level"),
        ("INSTANCE_REFERENCE_LEVEL_PARAM", "Reference Level")
    ],
    "Structural Columns": [
        ("FAMILY_BASE_LEVEL_PARAM", "Base Level"),
        ("FAMILY_LEVEL_PARAM", "Family Level")
    ]
}


# --------------------------------------------------
# 4. Category selection
# --------------------------------------------------

def select_categories():

    selected = forms.SelectFromList.show(
        CATEGORY_ORDER,
        title="BIM Quantity Extractor",
        button_name="Extract Quantities",
        multiselect=True,
        width=450,
        height=400
    )

    return selected or []


# --------------------------------------------------
# 5. Element collection
# --------------------------------------------------

def collect_elements(document, category):

    return list(
        DB.FilteredElementCollector(document)
        .OfCategory(category)
        .WhereElementIsNotElementType()
        .ToElements()
    )


# --------------------------------------------------
# 6. Quantity extraction
# --------------------------------------------------

def get_quantity(element, field):

    if element is None:
        return None

    config = QUANTITY_CONFIG[field]

    parameter = element.get_Parameter(
        config["parameter"]
    )

    if parameter is None:
        return None

    if not parameter.HasValue:
        return None

    if parameter.StorageType != DB.StorageType.Double:
        return None

    value = parameter.AsDouble()

    if math.isnan(value) or math.isinf(value):
        return None

    if value <= 0:
        return None

    return DB.UnitUtils.ConvertFromInternalUnits(
        value,
        config["unit"]
    )


def get_dimension(element, element_type, field):

    value = get_quantity(element_type, field)

    if value is None:
        value = get_quantity(element, field)

    return value


# --------------------------------------------------
# 7. Element identity
# --------------------------------------------------

def get_type_name(element_type):

    if element_type is None:
        return "Unknown Type"

    parameter = element_type.get_Parameter(
        DB.BuiltInParameter.SYMBOL_NAME_PARAM
    )

    if parameter is not None:

        name = parameter.AsString()

        if name:
            return name

    return "Unknown Type"


def get_family_name(element_type):

    if element_type is None:
        return "Unknown Family"

    return element_type.FamilyName


# --------------------------------------------------
# 8. Level identification
# --------------------------------------------------

def resolve_level(document, level_id):

    if level_id is None:
        return None

    if level_id == DB.ElementId.InvalidElementId:
        return None

    level = document.GetElement(level_id)

    if isinstance(level, DB.Level):
        return level

    return None


def get_level_from_parameter(element, document, parameter_name):

    parameter_id = getattr(
        DB.BuiltInParameter,
        parameter_name,
        None
    )

    if parameter_id is None:
        return None

    parameter = element.get_Parameter(parameter_id)

    if parameter is None:
        return None

    if not parameter.HasValue:
        return None

    if parameter.StorageType != DB.StorageType.ElementId:
        return None

    return resolve_level(
        document,
        parameter.AsElementId()
    )


def get_element_level(element, document, category_name):

    candidates = LEVEL_CONFIG.get(category_name, [])

    for parameter_name, source in candidates:

        level = get_level_from_parameter(
            element,
            document,
            parameter_name
        )

        if level is not None:

            return {
                "level": level.Name,
                "level_id": level.Id.Value,
                "level_source": source,
                "level_status": "RESOLVED"
            }

    level = resolve_level(
        document,
        element.LevelId
    )

    if level is not None:

        return {
            "level": level.Name,
            "level_id": level.Id.Value,
            "level_source": "Element.LevelId",
            "level_status": "RESOLVED"
        }

    return {
        "level": None,
        "level_id": None,
        "level_source": "",
        "level_status": "UNRESOLVED"
    }


# --------------------------------------------------
# 9. Wall classification
# --------------------------------------------------

def get_wall_kind(element_type):

    if not isinstance(element_type, DB.WallType):
        return "Unknown"

    if element_type.Kind == DB.WallKind.Basic:
        return "Basic"

    if element_type.Kind == DB.WallKind.Curtain:
        return "Curtain"

    if element_type.Kind == DB.WallKind.Stacked:
        return "Stacked"

    return "Other"


# --------------------------------------------------
# 10. Generic element extraction
# --------------------------------------------------

def extract_element_data(element, document, category_name):

    type_id = element.GetTypeId()
    element_type = document.GetElement(type_id)

    record = {
        "model_name": document.Title,
        "element_id": element.Id.Value,
        "unique_id": element.UniqueId,
        "category": category_name,
        "family": get_family_name(element_type),
        "type_name": get_type_name(element_type),
        "type_id": type_id.Value,
        "count": 1,
        "wall_kind": "",
        "volume_status": "N/A",
        "quantity_status": "OK",
        "missing_fields": [],
        "required_fields": []
    }

    # Initialize all quantity fields.

    for field in QUANTITY_CONFIG:
        record[field] = None

    record.update(
        get_element_level(
            element,
            document,
            category_name
        )
    )

    required_fields = list(
        CATEGORY_CONFIG[category_name]["quantities"]
    )

    # Apply wall-specific rules.

    if category_name == "Walls":

        wall_kind = get_wall_kind(element_type)
        record["wall_kind"] = wall_kind

        if not isinstance(element, DB.Wall):

            record["quantity_status"] = "UNSUPPORTED"
            return record

        if (element.IsStackedWallMember or
                wall_kind not in ("Basic", "Curtain")):

            record["quantity_status"] = "UNSUPPORTED"
            return record

        if wall_kind == "Curtain":
            required_fields.remove("volume_m3")

    record["required_fields"] = required_fields

    # Extract category-specific quantities.

    for field in required_fields:

        if field in ("width_mm", "height_mm"):

            value = get_dimension(
                element,
                element_type,
                field
            )

        else:

            value = get_quantity(element, field)

        record[field] = value

        if value is None:
            record["missing_fields"].append(field)

        if field == "volume_m3":

            if value is None:
                record["volume_status"] = "REVIEW"
            else:
                record["volume_status"] = "OK"

    if record["missing_fields"]:
        record["quantity_status"] = "REVIEW"

    return record


def extract_selected_categories(document, selected_categories):

    records = []

    for category_name in selected_categories:

        config = CATEGORY_CONFIG[category_name]

        elements = collect_elements(
            document,
            config["category"]
        )

        for element in elements:

            record = extract_element_data(
                element,
                document,
                category_name
            )

            records.append(record)

    return records


# --------------------------------------------------
# 11. Aggregation engine
# --------------------------------------------------

def create_quantity_summary():
    """Initialize an independent quantity accumulator."""

    return {
        "expected_count": 0,
        "valid_count": 0,
        "sum": 0.0,
        "min": None,
        "max": None
    }


def aggregate_quantity(summary, record, field):
    """Accumulate valid and applicable quantities."""

    if field not in record["required_fields"]:
        return

    summary["expected_count"] += 1

    value = record[field]

    if value is None:
        return

    summary["valid_count"] += 1
    summary["sum"] += value

    if summary["min"] is None or value < summary["min"]:
        summary["min"] = value

    if summary["max"] is None or value > summary["max"]:
        summary["max"] = value


def group_records(records):
    """Group supported elements by category, level and type."""

    groups = {}

    for record in records:

        if record["quantity_status"] == "UNSUPPORTED":
            continue

        type_key = record["type_id"]

        # Avoid merging elements with unresolved type IDs.

        if type_key <= 0:
            type_key = record["element_id"]

        key = (
            record["category"],
            record["level_id"],
            record["family"],
            record["type_id"],
            type_key,
            record["wall_kind"]
        )

        if key not in groups:

            groups[key] = {
                "category": record["category"],
                "level": record["level"],
                "level_id": record["level_id"],
                "family": record["family"],
                "type_name": record["type_name"],
                "type_id": record["type_id"],
                "wall_kind": record["wall_kind"],
                "count": 0,
                "review_count": 0,
                "quantities": {},
                "element_ids": []
            }

            for field in QUANTITY_CONFIG:

                groups[key]["quantities"][field] = (
                    create_quantity_summary()
                )

        group = groups[key]

        group["count"] += record["count"]

        group["element_ids"].append(
            record["element_id"]
        )

        if record["quantity_status"] == "REVIEW":
            group["review_count"] += 1

        for field in QUANTITY_CONFIG:

            aggregate_quantity(
                group["quantities"][field],
                record,
                field
            )

    return sorted(
        groups.values(),
        key=lambda group: (
            group["category"],
            group["level"] or "",
            group["family"],
            group["type_name"],
            group["type_id"]
        )
    )


# --------------------------------------------------
# 12. Aggregation formatting
# --------------------------------------------------

def format_aggregated_quantity(summary, field):

    expected = summary["expected_count"]
    valid = summary["valid_count"]

    if expected == 0:
        return "N/A"

    if valid == 0:
        return "Missing"

    aggregation = QUANTITY_CONFIG[field]["aggregation"]

    if aggregation == "SUM":

        text = "{:.2f}".format(summary["sum"])

    else:

        minimum = summary["min"]
        maximum = summary["max"]

        if abs(maximum - minimum) < 0.000001:

            text = "{:.2f}".format(minimum)

        else:

            text = "{:.2f} - {:.2f}".format(
                minimum,
                maximum
            )

    if valid < expected:

        text += " (Partial: {}/{})".format(
            valid,
            expected
        )

    return text


def format_quantity(record, field):

    if record["quantity_status"] == "UNSUPPORTED":
        return "Excluded"

    if field in record["missing_fields"]:
        return "Missing"

    value = record[field]

    if value is None:
        return "N/A"

    return "{:.2f}".format(value)


# --------------------------------------------------
# 13. Extraction summary
# --------------------------------------------------

def generate_extraction_summary(records, selected_categories):

    rows = []

    for category_name in CATEGORY_ORDER:

        if category_name not in selected_categories:
            continue

        category_records = [
            record for record in records
            if record["category"] == category_name
        ]

        ok_count = sum(
            1 for record in category_records
            if record["quantity_status"] == "OK"
        )

        review_count = sum(
            1 for record in category_records
            if record["quantity_status"] == "REVIEW"
        )

        unsupported_count = sum(
            1 for record in category_records
            if record["quantity_status"] == "UNSUPPORTED"
        )

        unresolved_count = sum(
            1 for record in category_records
            if record["level_status"] == "UNRESOLVED"
        )

        rows.append([
            category_name,
            len(category_records),
            ok_count,
            review_count,
            unsupported_count,
            unresolved_count
        ])

    output.print_table(
        table_data=rows,
        columns=[
            "Category",
            "Collected",
            "OK",
            "Review",
            "Unsupported",
            "Unresolved Levels"
        ],
        title="Extraction Summary"
    )


# --------------------------------------------------
# 14. Level summary
# --------------------------------------------------

def generate_level_summary(records):

    level_groups = {}

    for record in records:

        key = (
            record["level_id"],
            record["category"]
        )

        if key not in level_groups:

            level_groups[key] = {
                "level": record["level"] or "Unresolved",
                "category": record["category"],
                "count": 0
            }

        level_groups[key]["count"] += 1

    groups = sorted(
        level_groups.values(),
        key=lambda group: (
            group["level"],
            group["category"]
        )
    )

    rows = [
        [
            group["level"],
            group["category"],
            group["count"]
        ]
        for group in groups
    ]

    if rows:

        output.print_table(
            table_data=rows,
            columns=[
                "Associated Level",
                "Category",
                "Collected Instances"
            ],
            title="Elements by Level"
        )


# --------------------------------------------------
# 15. Aggregated quantity report
# --------------------------------------------------

def generate_aggregation_report(groups, selected_categories):

    output.print_md("# Aggregated Quantity Takeoff")

    for category_name in CATEGORY_ORDER:

        if category_name not in selected_categories:
            continue

        category_groups = [
            group for group in groups
            if group["category"] == category_name
        ]

        output.print_md(
            "## {}".format(category_name)
        )

        if not category_groups:

            output.print_md(
                "No supported elements found."
            )

            continue

        fields = CATEGORY_CONFIG[category_name]["quantities"]

        columns = [
            "Level",
            "Family",
            "Type",
            "Count"
        ]

        if category_name == "Walls":
            columns.append("Wall Kind")

        columns.extend([
            QUANTITY_CONFIG[field]["label"]
            for field in fields
        ])

        columns.append("Review")

        rows = []

        for group in category_groups:

            row = [
                group["level"] or "Unresolved",
                group["family"],
                group["type_name"],
                group["count"]
            ]

            if category_name == "Walls":
                row.append(group["wall_kind"])

            for field in fields:

                summary = group["quantities"][field]

                row.append(
                    format_aggregated_quantity(
                        summary,
                        field
                    )
                )

            row.append(group["review_count"])

            rows.append(row)

        output.print_table(
            table_data=rows,
            columns=columns
        )

        # Add category-level quantity totals.

        total_count = sum(
            group["count"]
            for group in category_groups
        )

        output.print_md(
            "**Supported instances:** {}".format(
                total_count
            )
        )

        for field in fields:

            if QUANTITY_CONFIG[field]["aggregation"] != "SUM":
                continue

            summary = create_quantity_summary()

            for group in category_groups:

                quantity = group["quantities"][field]

                summary["sum"] += quantity["sum"]

                summary["expected_count"] += (
                    quantity["expected_count"]
                )

                summary["valid_count"] += (
                    quantity["valid_count"]
                )

            output.print_md(
                "**Total {}:** {}".format(
                    QUANTITY_CONFIG[field]["label"],
                    format_aggregated_quantity(
                        summary,
                        field
                    )
                )
            )


# --------------------------------------------------
# 16. Detailed element report
# --------------------------------------------------

def generate_detail_report(records, selected_categories):

    output.print_md("# Detailed Element Quantities")

    for category_name in CATEGORY_ORDER:

        if category_name not in selected_categories:
            continue

        category_records = [
            record for record in records
            if record["category"] == category_name
        ]

        output.print_md(
            "## {}".format(category_name)
        )

        if not category_records:

            output.print_md("No elements found.")
            continue

        fields = CATEGORY_CONFIG[category_name]["quantities"]

        columns = [
            "Element ID",
            "Family",
            "Type",
            "Level"
        ]

        if category_name == "Walls":
            columns.append("Wall Kind")

        columns.extend([
            QUANTITY_CONFIG[field]["label"]
            for field in fields
        ])

        columns.append("Status")

        rows = []

        for record in category_records:

            row = [
                str(record["element_id"]),
                record["family"],
                record["type_name"],
                record["level"] or "Unresolved"
            ]

            if category_name == "Walls":
                row.append(record["wall_kind"])

            for field in fields:

                row.append(
                    format_quantity(record, field)
                )

            row.append(record["quantity_status"])

            rows.append(row)

        output.print_table(
            table_data=rows,
            columns=columns
        )


# --------------------------------------------------
# 17. Validation report
# --------------------------------------------------

def generate_validation_report(records, groups):

    output.print_md("# Validation Report")

    supported_count = sum(
        1 for record in records
        if record["quantity_status"] != "UNSUPPORTED"
    )

    grouped_count = sum(
        group["count"]
        for group in groups
    )

    unsupported_count = len(records) - supported_count

    unique_ids = set(
        record["element_id"]
        for record in records
    )

    count_match = supported_count == grouped_count

    unique_match = len(unique_ids) == len(records)

    reconciliation_rows = [
        [
            "Collected instances",
            len(records),
            "INFO"
        ],
        [
            "Unsupported instances",
            unsupported_count,
            "INFO"
        ],
        [
            "Supported instances",
            supported_count,
            "INFO"
        ],
        [
            "Grouped instances",
            grouped_count,
            "PASS" if count_match else "FAIL"
        ],
        [
            "Unique element IDs",
            len(unique_ids),
            "PASS" if unique_match else "FAIL"
        ]
    ]

    output.print_table(
        table_data=reconciliation_rows,
        columns=["Check", "Count", "Status"],
        title="Count Reconciliation"
    )

    # Reconcile raw and aggregated quantities.

    quantity_rows = []

    for category_name in CATEGORY_ORDER:

        category_records = [
            record for record in records
            if record["category"] == category_name
            and record["quantity_status"] != "UNSUPPORTED"
        ]

        if not category_records:
            continue

        category_groups = [
            group for group in groups
            if group["category"] == category_name
        ]

        fields = CATEGORY_CONFIG[category_name]["quantities"]

        for field in fields:

            if QUANTITY_CONFIG[field]["aggregation"] != "SUM":
                continue

            raw_values = [
                record[field]
                for record in category_records
                if field in record["required_fields"]
                and record[field] is not None
            ]

            expected_count = sum(
                1 for record in category_records
                if field in record["required_fields"]
            )

            if expected_count == 0:
                continue

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

            raw_total = sum(raw_values)

            tolerance = max(
                0.000001,
                abs(raw_total) * 0.000000001
            )

            matches = (
                abs(raw_total - group_total) <= tolerance
                and len(raw_values) == group_valid
                and expected_count == group_expected
            )

            if not matches:
                status = "FAIL"

            elif not raw_values:
                status = "NO DATA"

            elif len(raw_values) < expected_count:
                status = "PASS (Partial)"

            else:
                status = "PASS"

            quantity_rows.append([
                category_name,
                QUANTITY_CONFIG[field]["label"],
                "{:.4f}".format(raw_total)
                if raw_values else "Missing",
                "{:.4f}".format(group_total)
                if group_valid else "Missing",
                "{}/{}".format(
                    len(raw_values),
                    expected_count
                ),
                status
            ])

    if quantity_rows:

        output.print_table(
            table_data=quantity_rows,
            columns=[
                "Category",
                "Quantity",
                "Raw Total",
                "Grouped Total",
                "Valid / Expected",
                "Status"
            ],
            title="Quantity Reconciliation"
        )

    output.print_md("## Elements Requiring Quantity Review")

    review_records = [
        record for record in records
        if record["quantity_status"] == "REVIEW"
    ]

    if not review_records:

        output.print_md(
            "No missing required quantities found."
        )

    for record in review_records:

        element_link = output.linkify(
            DB.ElementId(record["element_id"])
        )

        missing = [
            QUANTITY_CONFIG[field]["label"]
            for field in record["missing_fields"]
        ]

        output.print_md(
            "- {} | {} | Missing: {}".format(
                record["category"],
                element_link,
                ", ".join(missing)
            )
        )

    output.print_md("## Unresolved Levels")

    unresolved_records = [
        record for record in records
        if record["level_status"] == "UNRESOLVED"
    ]

    if not unresolved_records:

        output.print_md(
            "All collected elements have a resolved level."
        )

    for record in unresolved_records:

        element_link = output.linkify(
            DB.ElementId(record["element_id"])
        )

        output.print_md(
            "- {} | {} | {}".format(
                record["category"],
                element_link,
                record["type_name"]
            )
        )

    output.print_md("## Unsupported Elements")

    unsupported_records = [
        record for record in records
        if record["quantity_status"] == "UNSUPPORTED"
    ]

    if not unsupported_records:

        output.print_md(
            "No unsupported elements found."
        )

    for record in unsupported_records:

        element_link = output.linkify(
            DB.ElementId(record["element_id"])
        )

        output.print_md(
            "- {} | {} | {}".format(
                record["category"],
                element_link,
                record["type_name"]
            )
        )


# --------------------------------------------------
# 18. Main report
# --------------------------------------------------

def generate_report(document, records, groups, selected_categories):

    output.print_md("# BIM Quantity Extractor")
    output.print_md("## Multi-Category Quantity Takeoff")

    output.print_md(
        "**Model:** {}".format(document.Title)
    )

    output.print_md(
        "**Total collected elements:** {}".format(
            len(records)
        )
    )

    output.print_md(
        "**Quantity groups:** {}".format(
            len(groups)
        )
    )

    resolved_count = sum(
        1 for record in records
        if record["level_status"] == "RESOLVED"
    )

    output.print_md(
        "**Levels resolved:** {}".format(
            resolved_count
        )
    )

    output.print_md(
        "**Levels unresolved:** {}".format(
            len(records) - resolved_count
        )
    )

    generate_extraction_summary(
        records,
        selected_categories
    )

    generate_level_summary(records)

    generate_aggregation_report(
        groups,
        selected_categories
    )

    generate_validation_report(
        records,
        groups
    )

    generate_detail_report(
        records,
        selected_categories
    )

    output.print_md("## Extraction Notes")

    notes = [
        "Quantities are grouped by category, associated "
        "level, family and type identity.",

        "Length, area and volume are summed.",

        "Width and height are displayed as values "
        "or ranges, not summed.",

        "Curtain Wall volume is outside the current scope.",

        "Unsupported elements are excluded from totals.",

        "Missing quantities are not treated as zero.",

        "Partial totals contain available values only.",

        "Multi-level elements are not split by floor.",

        "Internal reconciliation does not replace "
        "validation against native Revit schedules.",

        "Linked models are outside the current scope.",

        "No model elements have been modified."
    ]

    for note in notes:

        output.print_md(
            "- {}".format(note)
        )




# --------------------------------------------------
# 19. Main workflow
# --------------------------------------------------

def main():

    if doc is None:

        forms.alert(
            "No active Revit document found.",
            title="BIM Quantity Extractor"
        )

        return

    selected_categories = select_categories()

    if not selected_categories:
        return

    records = extract_selected_categories(
        doc,
        selected_categories
    )

    records.sort(
        key=lambda record: (
            record["category"],
            record["level"] or "",
            record["type_name"],
            record["element_id"]
        )
    )

    groups = group_records(records)

    generate_report(
        doc,
        records,
        groups,
        selected_categories
    )

    # Ask the user where to save the datasets.

    parent_folder = forms.pick_folder(
        title="Select CSV Export Folder"
    )

    if not parent_folder:

        output.print_md(
            "## CSV Export Cancelled"
        )

        return

    try:

        export_folder, exported_files = export_datasets(
            parent_folder,
            doc.Title,
            records,
            groups,
            selected_categories
        )

        output.print_md("## CSV Export Complete")

        output.print_md(
            "**Destination:** {}".format(
                export_folder
            )
        )

        rows = []

        for exported_file in exported_files:

            rows.append([
                exported_file["filename"],
                exported_file["row_count"],
                "Exported"
            ])

        output.print_table(
            table_data=rows,
            columns=[
                "Dataset",
                "Records",
                "Status"
            ],
            title="Exported CSV Datasets"
        )

        forms.alert(
            "Three CSV datasets exported successfully.",
            title="BIM Quantity Extractor"
        )

    except Exception as error:

        output.print_md("## CSV Export Failed")

        output.print_md(
            "**Error:** {}".format(error)
        )

        forms.alert(
            "CSV export failed. Check the output report.",
            title="BIM Quantity Extractor"
        )

if __name__ == "__main__":
    main()