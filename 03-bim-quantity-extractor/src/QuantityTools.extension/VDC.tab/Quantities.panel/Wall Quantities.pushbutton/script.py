
# -*- coding: utf-8 -*-

"""BIM Quantity Extractor - Wall Quantities MVP."""

import csv
import codecs

from collections import defaultdict

from pyrevit import revit, DB, forms, script


doc = revit.doc
output = script.get_output()


# --------------------------------------------------
# 1. Collect model elements
# --------------------------------------------------

def collect_walls(document):
    """Collect wall instances from the active document."""
    return list(
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_Walls)
        .WhereElementIsNotElementType()
        .ToElements()
    )


# --------------------------------------------------
# 2. Read and convert quantities
# --------------------------------------------------

def get_quantity(element, parameter_id, unit_id):
    """Return a quantity in SI units or None."""
    parameter = element.get_Parameter(parameter_id)

    if parameter is None:
        return None

    if not parameter.HasValue:
        return None

    if parameter.StorageType != DB.StorageType.Double:
        return None

    value = parameter.AsDouble()

    if value <= 0:
        return None

    return DB.UnitUtils.ConvertFromInternalUnits(
        value, unit_id
    )


def get_type_name(element_type):
    """Return a stable display name for the type."""
    parameter = element_type.get_Parameter(
        DB.BuiltInParameter.SYMBOL_NAME_PARAM
    )

    if parameter is not None:
        name = parameter.AsString()
        if name:
            return name

    return "Unknown Type"


# --------------------------------------------------
# 3. Extract BIM data
# --------------------------------------------------

def extract_wall_data(wall, document):
    """Create a structured dictionary for one wall."""
    type_id = wall.GetTypeId()
    wall_type = document.GetElement(type_id)

    if wall_type is None:
        family = "Unknown Family"
        type_name = "Unknown Type"
    else:
        family = wall_type.FamilyName
        type_name = get_type_name(wall_type)

    length = get_quantity(
        wall,
        DB.BuiltInParameter.CURVE_ELEM_LENGTH,
        DB.UnitTypeId.Meters
    )

    area = get_quantity(
        wall,
        DB.BuiltInParameter.HOST_AREA_COMPUTED,
        DB.UnitTypeId.SquareMeters
    )

    volume = get_quantity(
        wall,
        DB.BuiltInParameter.HOST_VOLUME_COMPUTED,
        DB.UnitTypeId.CubicMeters
    )

    status = "OK"

    if any(value is None for value in
           (length, area, volume)):
        status = "REVIEW"

    return {
        "model_name": document.Title,
        "element_id": wall.Id.IntegerValue,
        "unique_id": wall.UniqueId,
        "family": family,
        "type_name": type_name,
        "type_id": type_id.IntegerValue,
        "length_m": length,
        "area_m2": area,
        "volume_m3": volume,
        "quantity_status": status
    }


# --------------------------------------------------
# 4. Aggregate quantities
# --------------------------------------------------

def group_wall_data(wall_data):
    """Group wall records by family and type ID."""
    groups = {}

    for wall in wall_data:
        key = (
            wall["family"],
            wall["type_id"],
            wall["type_name"]
        )

        if key not in groups:
            groups[key] = {
                "family": wall["family"],
                "type_name": wall["type_name"],
                "count": 0,
                "length_m": 0.0,
                "area_m2": 0.0,
                "volume_m3": 0.0,
                "review_count": 0,
                "valid_length_count": 0,
                "valid_area_count": 0,
                "valid_volume_count": 0
            }

        group = groups[key]
        group["count"] += 1

        if wall["quantity_status"] == "REVIEW":
            group["review_count"] += 1

        for field in ("length_m", "area_m2", "volume_m3"):
            value = wall[field]

            if value is not None:
                group[field] += value
                group["valid_" + field.split("_")[0] +
                      "_count"] += 1

    return groups


# --------------------------------------------------
# 5. Generate pyRevit report
# --------------------------------------------------

def generate_report(wall_data, groups):
    """Display extraction and grouping results."""
    output.print_md("# BIM Quantity Extractor")
    output.print_md("## Wall Quantity Report")

    output.print_md(
        "**Model:** {}".format(doc.Title)
    )

    output.print_md(
        "**Wall instances:** {}".format(len(wall_data))
    )

    output.print_md(
        "**Wall types used:** {}".format(len(groups))
    )

    review_count = sum(
        1 for wall in wall_data
        if wall["quantity_status"] == "REVIEW"
    )

    output.print_md(
        "**Elements requiring review:** {}".format(
            review_count
        )
    )

    output.print_md("## Quantities by Wall Type")

    output.print_md(
        "| Family | Type | Count | Length (m) | "
        "Area (m2) | Volume (m3) | Review |"
    )
    output.print_md(
        "|---|---|---:|---:|---:|---:|---:|"
    )

    for key in sorted(groups):
        group = groups[key]

        output.print_md(
            "| {} | {} | {} | {:.2f} | {:.2f} | "
            "{:.2f} | {} |".format(
                group["family"].replace("|", "/"),
                group["type_name"].replace("|", "/"),
                group["count"],
                group["length_m"],
                group["area_m2"],
                group["volume_m3"],
                group["review_count"]
            )
        )

    output.print_md("## Elements Requiring Review")

    if review_count == 0:
        output.print_md(
            "No missing or non-positive quantities found."
        )
    else:
        for wall in wall_data:
            if wall["quantity_status"] != "REVIEW":
                continue

            missing = []

            for field in ("length_m", "area_m2", "volume_m3"):
                if wall[field] is None:
                    missing.append(field)

            element_link = output.linkify(
                DB.ElementId(wall["element_id"])
            )

            output.print_md(
                "- Wall {}: {}".format(
                    element_link, ", ".join(missing)
                )
            )

    output.print_md(
        "*Totals include available positive values only. "
        "Review incomplete groups before using them "
        "for estimating.*"
    )


# --------------------------------------------------
# 6. Export to CSV
# --------------------------------------------------

def format_csv_value(value):
    """Convert a value to a CSV-safe UTF-8 string."""
    if value is None:
        return ""

    if isinstance(value, float):
        return "{:.6f}".format(value)

    if isinstance(value, unicode):
        return value.encode("utf-8")

    return str(value)


def export_csv(wall_data, file_path):
    """Write wall instance records as UTF-8 CSV."""
    headers = [
        "model_name",
        "element_id",
        "unique_id",
        "family",
        "type_name",
        "type_id",
        "length_m",
        "area_m2",
        "volume_m3",
        "quantity_status"
    ]

    with open(file_path, "wb") as csv_file:
        csv_file.write(codecs.BOM_UTF8)

        writer = csv.writer(csv_file)
        writer.writerow(headers)

        for wall in wall_data:
            row = [
                format_csv_value(wall[field])
                for field in headers
            ]
            writer.writerow(row)


# --------------------------------------------------
# 7. Main workflow
# --------------------------------------------------

def main():
    if doc is None:
        forms.alert(
            "No active Revit document found.",
            title="Wall Quantities"
        )
        return

    walls = collect_walls(doc)

    if not walls:
        forms.alert(
            "No wall instances found in the active model.",
            title="Wall Quantities"
        )
        return

    wall_data = [
        extract_wall_data(wall, doc)
        for wall in walls
    ]

    wall_data.sort(key=lambda x: x["element_id"])

    groups = group_wall_data(wall_data)

    generate_report(wall_data, groups)

    file_path = forms.save_file(
        file_ext="csv",
        default_name="wall_quantities.csv",
        title="Export Wall Quantities"
    )

    if not file_path:
        output.print_md("**CSV export cancelled.**")
        return

    try:
        export_csv(wall_data, file_path)

        output.print_md(
            "## CSV Export Complete"
        )
        output.print_md(
            "**Records exported:** {}".format(
                len(wall_data)
            )
        )
        output.print_md(
            "**File:** `{}`".format(file_path)
        )

    except Exception as error:
        output.print_md(
            "**CSV export failed:** {}".format(error)
        )


if __name__ == "__main__":
    main()
