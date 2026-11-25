
# -*- coding: utf-8 -*-

"""BIM Quantity Extractor - Multi-Category and Level Identification."""

import math

from pyrevit import revit, DB, forms, script


doc = revit.doc
output = script.get_output()


# --------------------------------------------------
# 1. Quantity configuration
# --------------------------------------------------

QUANTITY_CONFIG = {
    "length_m": {
        "parameter": DB.BuiltInParameter.CURVE_ELEM_LENGTH,
        "unit": DB.UnitTypeId.Meters
    },
    "area_m2": {
        "parameter": DB.BuiltInParameter.HOST_AREA_COMPUTED,
        "unit": DB.UnitTypeId.SquareMeters
    },
    "volume_m3": {
        "parameter": DB.BuiltInParameter.HOST_VOLUME_COMPUTED,
        "unit": DB.UnitTypeId.CubicMeters
    },
    "width_mm": {
        "parameter": DB.BuiltInParameter.FAMILY_WIDTH_PARAM,
        "unit": DB.UnitTypeId.Millimeters
    },
    "height_mm": {
        "parameter": DB.BuiltInParameter.FAMILY_HEIGHT_PARAM,
        "unit": DB.UnitTypeId.Millimeters
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

QUANTITY_LABELS = {
    "length_m": "Length (m)",
    "area_m2": "Area (m2)",
    "volume_m3": "Volume (m3)",
    "width_mm": "Width (mm)",
    "height_mm": "Height (mm)"
}


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
# 5. Generic element collector
# --------------------------------------------------

def collect_elements(document, category):

    return list(
        DB.FilteredElementCollector(document)
        .OfCategory(category)
        .WhereElementIsNotElementType()
        .ToElements()
    )


# --------------------------------------------------
# 6. Parameter extraction
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

    """Return a Level object from a valid ElementId."""

    if level_id is None:
        return None

    if level_id == DB.ElementId.InvalidElementId:
        return None

    level = document.GetElement(level_id)

    if isinstance(level, DB.Level):
        return level

    return None


def get_level_from_parameter(element, document, parameter_name):

    """Resolve a level using a built-in parameter."""

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

    """Resolve the associated or base level."""

    candidates = LEVEL_CONFIG.get(category_name, [])

    # Try category-specific level parameters first.

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

    # Fall back to the general LevelId property.

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

    # Do not assign an estimated level.

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
        "length_m": None,
        "area_m2": None,
        "volume_m3": None,
        "width_mm": None,
        "height_mm": None,
        "volume_status": "N/A",
        "quantity_status": "OK",
        "missing_fields": []
    }

    # Add level information to the element record.

    level_data = get_element_level(
        element,
        document,
        category_name
    )

    record.update(level_data)

    required_fields = list(
        CATEGORY_CONFIG[category_name]["quantities"]
    )

    # Apply wall-specific extraction rules.

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

    # Extract required quantities.

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


# --------------------------------------------------
# 11. Extract selected categories
# --------------------------------------------------

def extract_selected_categories(document, selected_categories):

    all_records = []

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

            all_records.append(record)

    return all_records


# --------------------------------------------------
# 12. Format report quantities
# --------------------------------------------------

def format_quantity(record, field):

    value = record[field]

    if record["quantity_status"] == "UNSUPPORTED":
        return "Excluded"

    if field in record["missing_fields"]:
        return "Missing"

    if value is None:
        return "N/A"

    return "{:.2f}".format(value)


# --------------------------------------------------
# 13. Level summary
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

    rows = []

    groups = sorted(
        level_groups.values(),
        key=lambda group: (
            group["level"],
            group["category"]
        )
    )

    for group in groups:

        rows.append([
            group["level"],
            group["category"],
            group["count"]
        ])

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
# 14. Generate report
# --------------------------------------------------

def generate_report(document, records, selected_categories):

    output.print_md("# BIM Quantity Extractor")
    output.print_md("## Multi-Category Quantity Report")

    output.print_md(
        "**Model:** {}".format(document.Title)
    )

    output.print_md(
        "**Total collected elements:** {}".format(
            len(records)
        )
    )

    resolved_count = sum(
        1 for record in records
        if record["level_status"] == "RESOLVED"
    )

    unresolved_count = len(records) - resolved_count

    output.print_md(
        "**Levels resolved:** {}".format(resolved_count)
    )

    output.print_md(
        "**Levels unresolved:** {}".format(unresolved_count)
    )

    summary_rows = []

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

        unresolved = sum(
            1 for record in category_records
            if record["level_status"] == "UNRESOLVED"
        )

        summary_rows.append([
            category_name,
            len(category_records),
            ok_count,
            review_count,
            unsupported_count,
            unresolved
        ])

    output.print_table(
        table_data=summary_rows,
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

    generate_level_summary(records)

    # Display individual quantities by category.

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
            QUANTITY_LABELS[field]
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

    # Report missing quantities.

    output.print_md("## Elements Requiring Quantity Review")

    review_records = [
        record for record in records
        if record["quantity_status"] == "REVIEW"
    ]

    if not review_records:

        output.print_md(
            "No missing required quantities found."
        )

    else:

        for record in review_records:

            element_link = output.linkify(
                DB.ElementId(record["element_id"])
            )

            missing = [
                QUANTITY_LABELS[field]
                for field in record["missing_fields"]
            ]

            output.print_md(
                "- {} | {} | Missing: {}".format(
                    record["category"],
                    element_link,
                    ", ".join(missing)
                )
            )

    # Report unresolved levels.

    output.print_md("## Unresolved Levels")

    if unresolved_count == 0:

        output.print_md(
            "All collected elements have a resolved level."
        )

    else:

        for record in records:

            if record["level_status"] != "UNRESOLVED":
                continue

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

    output.print_md("## Extraction Notes")

    output.print_md(
        "- Levels represent associated or base levels."
    )

    output.print_md(
        "- Multi-level elements are not split by floor."
    )

    output.print_md(
        "- Level counts include all collected instances."
    )

    output.print_md(
        "- Unresolved levels are not estimated."
    )

    output.print_md(
        "- Unsupported elements are excluded "
        "from physical quantity extraction."
    )

    output.print_md(
        "- N/A means the quantity is outside "
        "the current extraction scope."
    )

    output.print_md(
        "- No model elements have been modified."
    )


# --------------------------------------------------
# 15. Main workflow
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

    generate_report(
        doc,
        records,
        selected_categories
    )


if __name__ == "__main__":
    main()
