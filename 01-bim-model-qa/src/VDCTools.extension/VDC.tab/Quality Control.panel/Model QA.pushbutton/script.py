
# -*- coding: utf-8 -*-

"""
BIM MODEL QA CHECKER
Project: BIM Automation Portfolio
Environment: Revit 2024 + pyRevit + IronPython

Features:
- Door inventory
- Missing Mark detection
- Duplicate Mark detection
- Missing Dimensions review
- Invalid Dimensions detection
- Interactive QA report
"""

from pyrevit import revit, DB, script


# ============================================================
# 1. REVIT DOCUMENT
# ============================================================

doc = revit.doc


# ============================================================
# 2. DATA COLLECTION
# ============================================================

def collect_doors(document):
    """Collect all door instances in the active model."""

    collector = DB.FilteredElementCollector(document)

    doors = list(
        collector
        .OfCategory(DB.BuiltInCategory.OST_Doors)
        .WhereElementIsNotElementType()
    )

    return doors


# ============================================================
# 3. PARAMETER HELPERS
# ============================================================

def get_string_parameter(element, parameter_id):
    """Read a text parameter safely."""

    if element is None:
        return None

    param = element.get_Parameter(parameter_id)

    if not param:
        return None

    if not param.HasValue:
        return None

    if param.StorageType != DB.StorageType.String:
        return None

    return param.AsString()


def get_dimension_mm(element, parameter_id):
    """Read a length parameter and convert it to mm."""

    if element is None:
        return None

    param = element.get_Parameter(parameter_id)

    if not param:
        return None

    if not param.HasValue:
        return None

    if param.StorageType != DB.StorageType.Double:
        return None

    value_internal = param.AsDouble()

    return DB.UnitUtils.ConvertFromInternalUnits(
        value_internal,
        DB.UnitTypeId.Millimeters
    )


# ============================================================
# 4. DATA EXTRACTION
# ============================================================

def extract_door_data(door, document):
    """Convert a Revit door into a structured dictionary."""

    type_id = door.GetTypeId()
    door_type = None

    if type_id != DB.ElementId.InvalidElementId:
        door_type = document.GetElement(type_id)

    # Instance parameter
    mark = get_string_parameter(
        door,
        DB.BuiltInParameter.ALL_MODEL_MARK
    )

    # Default values
    type_name = None
    width_mm = None
    height_mm = None

    if door_type:

        # Use built-in parameter to avoid IronPython
        # inherited Name property access issues.
        type_name = get_string_parameter(
            door_type,
            DB.BuiltInParameter.SYMBOL_NAME_PARAM
        )

        width_mm = get_dimension_mm(
            door_type,
            DB.BuiltInParameter.DOOR_WIDTH
        )

        height_mm = get_dimension_mm(
            door_type,
            DB.BuiltInParameter.DOOR_HEIGHT
        )

    # Instance fallback for dimension parameters
    if width_mm is None:
        width_mm = get_dimension_mm(
            door,
            DB.BuiltInParameter.DOOR_WIDTH
        )

    if height_mm is None:
        height_mm = get_dimension_mm(
            door,
            DB.BuiltInParameter.DOOR_HEIGHT
        )

    return {
        "element_id": door.Id,
        "type_id": type_id,
        "mark": mark,
        "type_name": type_name,
        "width_mm": width_mm,
        "height_mm": height_mm
    }


# ============================================================
# 5. BIM QA VALIDATION
# ============================================================

def validate_doors(all_door_data):
    """Apply BIM quality rules to extracted door data."""

    issues = []
    marks_by_value = {}

    for door in all_door_data:

        element_id = door["element_id"]
        mark = door["mark"]
        width = door["width_mm"]
        height = door["height_mm"]

        # RULE 01: Missing Mark
        if mark is None or not mark.strip():

            issues.append({
                "element_id": element_id,
                "rule": "Missing Mark",
                "severity": "ERROR",
                "description": "Door Mark is empty or missing"
            })

        else:
            normalized_mark = mark.strip().upper()

            if normalized_mark not in marks_by_value:
                marks_by_value[normalized_mark] = []

            marks_by_value[normalized_mark].append(element_id)

        # RULE 02: Missing Dimensions
        if width is None or height is None:

            issues.append({
                "element_id": element_id,
                "rule": "Missing Dimensions",
                "severity": "REVIEW",
                "description": (
                    "Width or Height could not be retrieved"
                )
            })

        # RULE 03: Invalid Dimensions
        elif width <= 0 or height <= 0:

            issues.append({
                "element_id": element_id,
                "rule": "Invalid Dimensions",
                "severity": "ERROR",
                "description": (
                    "Width and Height must be greater than zero"
                )
            })

    # RULE 04: Duplicate Mark
    for mark, element_ids in marks_by_value.items():

        if len(element_ids) > 1:

            for element_id in element_ids:

                issues.append({
                    "element_id": element_id,
                    "rule": "Duplicate Mark",
                    "severity": "WARNING",
                    "description": (
                        "Mark '{}' is assigned to {} doors"
                    ).format(mark, len(element_ids))
                })

    return issues


# ============================================================
# 6. REPORT HELPERS
# ============================================================

def format_dimension(value):
    """Format dimension values for the report."""

    if value is None:
        return "N/A"

    return "{:.0f} mm".format(value)


def get_severity_counts(issues):
    """Count findings by severity."""

    counts = {
        "ERROR": 0,
        "WARNING": 0,
        "REVIEW": 0
    }

    for issue in issues:

        severity = issue["severity"]

        if severity in counts:
            counts[severity] += 1

    return counts


# ============================================================
# 7. INTERACTIVE QA REPORT
# ============================================================

def generate_report(document, all_door_data, issues):
    """Generate a formatted pyRevit report."""

    output = script.get_output()
    output.set_title("BIM Model QA Checker")

    counts = get_severity_counts(issues)

    # HEADER
    output.print_md("# BIM Model QA Checker")
    output.print_md(
        "**Model:** {}".format(document.Title)
    )

    # SUMMARY
    output.print_md("## Quality Summary")

    summary_rows = [
        ["Total Doors", len(all_door_data)],
        ["Errors", counts["ERROR"]],
        ["Warnings", counts["WARNING"]],
        ["Needs Review", counts["REVIEW"]],
        ["Total Findings", len(issues)]
    ]

    output.print_table(
        table_data=summary_rows,
        columns=["Metric", "Count"]
    )

    # DOOR INVENTORY
    output.print_md("## Door Inventory")

    inventory_rows = []

    for door in all_door_data:

        inventory_rows.append([
            str(door["element_id"]),
            door["mark"] or "MISSING",
            door["type_name"] or "Unknown",
            format_dimension(door["width_mm"]),
            format_dimension(door["height_mm"])
        ])

    output.print_table(
        table_data=inventory_rows,
        columns=[
            "Element ID",
            "Mark",
            "Door Type",
            "Width",
            "Height"
        ]
    )

    # QUALITY FINDINGS
    output.print_md("## QA Findings")

    if not issues:
        output.print_md(
            "**PASS:** No issues detected by the current rules."
        )
        return

    issue_rows = []

    for issue in issues:

        issue_rows.append([
            str(issue["element_id"]),
            issue["severity"],
            issue["rule"],
            issue["description"]
        ])

    output.print_table(
        table_data=issue_rows,
        columns=[
            "Element ID",
            "Severity",
            "Rule",
            "Description"
        ]
    )

    # CLICKABLE REVIT LINKS
    output.print_md("## Locate Issues in Revit")

    for issue in issues:

        element_link = output.linkify(
            issue["element_id"]
        )

        # Use print() because linkify produces HTML
        # that should be rendered without Markdown escaping.
        print("{} | {} | {}".format(
            element_link,
            issue["severity"],
            issue["rule"]
        ))

        print("")

    output.print_md(
        "---\n"
        "*This report does not modify the Revit model. "
        "Missing dimension parameters may require manual review.*"
    )


# ============================================================
# 8. MAIN EXECUTION
# ============================================================

def main():

    # Step 1: Collect elements
    doors = collect_doors(doc)

    # Step 2: Extract structured data
    all_door_data = []

    for door in doors:

        data = extract_door_data(door, doc)

        all_door_data.append(data)

    # Step 3: Apply BIM validation rules
    issues = validate_doors(all_door_data)

    # Step 4: Generate report
    generate_report(
        doc,
        all_door_data,
        issues
    )


# Single entry point
if __name__ == "__main__":
    main()
