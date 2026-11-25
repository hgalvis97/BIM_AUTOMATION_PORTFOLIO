
# -*- coding: utf-8 -*-

"""BIM Quantity Extractor - Wall Quantity Validation."""

import csv
import codecs
import math

from pyrevit import revit, DB, forms, script


doc = revit.doc
output = script.get_output()


# --------------------------------------------------
# 1. Collect wall instances
# --------------------------------------------------

def collect_walls(document):
    return list(
        DB.FilteredElementCollector(document)
        .OfClass(DB.Wall)
        .OfCategory(DB.BuiltInCategory.OST_Walls)
        .WhereElementIsNotElementType()
        .ToElements()
    )


# --------------------------------------------------
# 2. Read and convert quantities
# --------------------------------------------------

def get_quantity(element, parameter_id, unit_id):
    parameter = element.get_Parameter(parameter_id)

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
        value, unit_id
    )


def get_type_name(element_type):
    parameter = element_type.get_Parameter(
        DB.BuiltInParameter.SYMBOL_NAME_PARAM
    )

    if parameter is not None:
        name = parameter.AsString()

        if name:
            return name

    return "Unknown Type"


# --------------------------------------------------
# 3. Identify wall kind
# --------------------------------------------------

def get_wall_kind(wall_type):
    if wall_type is None:
        return "Unknown"

    if wall_type.Kind == DB.WallKind.Basic:
        return "Basic"

    if wall_type.Kind == DB.WallKind.Curtain:
        return "Curtain"

    if wall_type.Kind == DB.WallKind.Stacked:
        return "Stacked"

    return "Other"


# --------------------------------------------------
# 4. Extract and validate wall data
# --------------------------------------------------

def extract_wall_data(wall, document):
    type_id = wall.GetTypeId()
    wall_type = document.GetElement(type_id)

    if wall_type is None:
        family = "Unknown Family"
        type_name = "Unknown Type"
    else:
        family = wall_type.FamilyName
        type_name = get_type_name(wall_type)

    wall_kind = get_wall_kind(wall_type)

    length = None
    area = None
    volume = None

    quantity_status = "OK"
    volume_status = "N/A"

    # Exclude stacked walls and their members.
    # This prevents potential double counting.

    if (wall.IsStackedWallMember or
            wall_kind not in ("Basic", "Curtain")):

        quantity_status = "UNSUPPORTED"

    else:

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

        # Volume is required for Basic Walls.

        if wall_kind == "Basic":

            volume = get_quantity(
                wall,
                DB.BuiltInParameter.HOST_VOLUME_COMPUTED,
                DB.UnitTypeId.CubicMeters
            )

            if volume is None:
                volume_status = "REVIEW"
            else:
                volume_status = "OK"

        # Curtain Wall volume is outside the MVP scope.

        if length is None or area is None:
            quantity_status = "REVIEW"

        if volume_status == "REVIEW":
            quantity_status = "REVIEW"

    return {
        "model_name": document.Title,
        "element_id": wall.Id.Value,
        "unique_id": wall.UniqueId,
        "family": family,
        "type_name": type_name,
        "type_id": type_id.Value,
        "wall_kind": wall_kind,
        "length_m": length,
        "area_m2": area,
        "volume_m3": volume,
        "volume_status": volume_status,
        "quantity_status": quantity_status
    }


# --------------------------------------------------
# 5. Aggregate wall quantities
# --------------------------------------------------

def group_wall_data(wall_data):
    groups = {}

    for wall in wall_data:

        if wall["quantity_status"] == "UNSUPPORTED":
            continue

        key = (
            wall["wall_kind"],
            wall["family"],
            wall["type_id"],
            wall["type_name"]
        )

        if key not in groups:
            groups[key] = {
                "wall_kind": wall["wall_kind"],
                "family": wall["family"],
                "type_name": wall["type_name"],
                "count": 0,
                "length_m": 0.0,
                "area_m2": 0.0,
                "volume_m3": 0.0,
                "valid_length_count": 0,
                "valid_area_count": 0,
                "valid_volume_count": 0,
                "review_count": 0
            }

        group = groups[key]
        group["count"] += 1

        if wall["quantity_status"] == "REVIEW":
            group["review_count"] += 1

        fields = (
            ("length_m", "valid_length_count"),
            ("area_m2", "valid_area_count"),
            ("volume_m3", "valid_volume_count")
        )

        for field, count_field in fields:

            value = wall[field]

            if value is not None:
                group[field] += value
                group[count_field] += 1

    return groups


# --------------------------------------------------
# 6. Format quantities for reporting
# --------------------------------------------------

def format_total(total, valid_count, expected_count):

    if expected_count == 0:
        return "N/A"

    if valid_count == 0:
        return "Missing"

    if valid_count < expected_count:
        return "{:.2f} (Partial)".format(total)

    return "{:.2f}".format(total)


# --------------------------------------------------
# 7. Generate pyRevit report
# --------------------------------------------------

def generate_report(wall_data, groups):

    basic_count = sum(
        1 for wall in wall_data
        if wall["wall_kind"] == "Basic"
        and wall["quantity_status"] != "UNSUPPORTED"
    )

    curtain_count = sum(
        1 for wall in wall_data
        if wall["wall_kind"] == "Curtain"
        and wall["quantity_status"] != "UNSUPPORTED"
    )

    review_count = sum(
        1 for wall in wall_data
        if wall["quantity_status"] == "REVIEW"
    )

    unsupported_count = sum(
        1 for wall in wall_data
        if wall["quantity_status"] == "UNSUPPORTED"
    )

    output.print_md("# BIM Quantity Extractor")
    output.print_md("## Wall Quantity Report")

    output.print_md("**Model:** {}".format(doc.Title))

    output.print_md(
        "**Wall instances:** {}".format(len(wall_data))
    )

    output.print_md(
        "**Supported wall types:** {}".format(len(groups))
    )

    output.print_md(
        "**Basic Walls:** {}".format(basic_count)
    )

    output.print_md(
        "**Curtain Walls:** {}".format(curtain_count)
    )

    output.print_md(
        "**Elements requiring review:** {}".format(
            review_count
        )
    )

    output.print_md(
        "**Unsupported elements:** {}".format(
            unsupported_count
        )
    )

    rows = []

    for key in sorted(groups):

        group = groups[key]

        count = group["count"]

        length = format_total(
            group["length_m"],
            group["valid_length_count"],
            count
        )

        area = format_total(
            group["area_m2"],
            group["valid_area_count"],
            count
        )

        expected_volume_count = count

        if group["wall_kind"] == "Curtain":
            expected_volume_count = 0

        volume = format_total(
            group["volume_m3"],
            group["valid_volume_count"],
            expected_volume_count
        )

        rows.append([
            group["wall_kind"],
            group["family"].replace("|", "/"),
            group["type_name"].replace("|", "/"),
            count,
            length,
            area,
            volume,
            group["review_count"]
        ])

    if rows:
        output.print_table(
            table_data=rows,
            columns=[
                "Kind",
                "Family",
                "Type",
                "Count",
                "Length (m)",
                "Area (m2)",
                "Volume (m3)",
                "Review"
            ],
            title="Quantities by Wall Type"
        )

    output.print_md("## Elements Requiring Review")

    if review_count == 0:
        output.print_md(
            "No missing required quantities found."
        )

    else:
        for wall in wall_data:

            if wall["quantity_status"] != "REVIEW":
                continue

            missing = []

            if wall["length_m"] is None:
                missing.append("Length")

            if wall["area_m2"] is None:
                missing.append("Area")

            if wall["volume_status"] == "REVIEW":
                missing.append("Volume")

            element_link = output.linkify(
                DB.ElementId(wall["element_id"])
            )

            output.print_md(
                "- Wall {}: {}".format(
                    element_link,
                    ", ".join(missing)
                )
            )

    if unsupported_count > 0:

        output.print_md("## Unsupported Elements")

        for wall in wall_data:

            if wall["quantity_status"] != "UNSUPPORTED":
                continue

            element_link = output.linkify(
                DB.ElementId(wall["element_id"])
            )

            output.print_md(
                "- Wall {}: {} - {}".format(
                    element_link,
                    wall["wall_kind"],
                    wall["type_name"]
                )
            )

    output.print_md("## Quantity Notes")

    output.print_md(
        "- Curtain Wall volume is not applicable "
        "within the current extraction scope."
    )

    output.print_md(
        "- Missing quantities are not treated as zero."
    )

    output.print_md(
        "- Partial totals include available quantities only."
    )

    output.print_md(
        "- Unsupported elements are excluded from totals."
    )


# --------------------------------------------------
# 8. Export CSV
# --------------------------------------------------

def format_csv_value(value):

    if value is None:
        return ""

    if isinstance(value, float):
        return "{:.6f}".format(value)

    if isinstance(value, unicode):
        return value.encode("utf-8")

    return str(value)


def export_csv(wall_data, file_path):

    headers = [
        "model_name",
        "element_id",
        "unique_id",
        "family",
        "type_name",
        "type_id",
        "wall_kind",
        "length_m",
        "area_m2",
        "volume_m3",
        "volume_status",
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
# 9. Main workflow
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
            "No wall instances found.",
            title="Wall Quantities"
        )
        return

    wall_data = [
        extract_wall_data(wall, doc)
        for wall in walls
    ]

    wall_data.sort(
        key=lambda wall: wall["element_id"]
    )

    groups = group_wall_data(wall_data)

    generate_report(wall_data, groups)

    file_path = forms.save_file(
        file_ext="csv",
        default_name="wall_quantities_v2.csv",
        title="Export Wall Quantities"
    )

    if not file_path:
        output.print_md("**CSV export cancelled.**")
        return

    try:

        export_csv(wall_data, file_path)

        output.print_md("## CSV Export Complete")

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
