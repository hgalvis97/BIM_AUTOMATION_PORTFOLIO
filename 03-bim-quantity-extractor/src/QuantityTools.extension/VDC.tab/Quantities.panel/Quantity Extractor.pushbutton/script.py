
# -*- coding: utf-8 -*-

"""BIM Quantity Extractor - Multi-Category Collection."""

from pyrevit import revit, DB, forms, script


doc = revit.doc
output = script.get_output()


# --------------------------------------------------
# 1. Category configuration
# --------------------------------------------------

CATEGORY_CONFIG = {
    "Walls": DB.BuiltInCategory.OST_Walls,
    "Floors": DB.BuiltInCategory.OST_Floors,
    "Doors": DB.BuiltInCategory.OST_Doors,
    "Windows": DB.BuiltInCategory.OST_Windows,
    "Structural Columns": DB.BuiltInCategory.OST_StructuralColumns
}

CATEGORY_ORDER = [
    "Walls",
    "Floors",
    "Doors",
    "Windows",
    "Structural Columns"
]


# --------------------------------------------------
# 2. Category selection
# --------------------------------------------------

def select_categories():
    """Allow the user to select multiple BIM categories."""

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
# 3. Generic element collector
# --------------------------------------------------

def collect_elements(document, category):
    """Collect element instances from a given category."""

    return list(
        DB.FilteredElementCollector(document)
        .OfCategory(category)
        .WhereElementIsNotElementType()
        .ToElements()
    )


# --------------------------------------------------
# 4. Collect selected categories
# --------------------------------------------------

def collect_selected_categories(document, selected_categories):
    """Collect and organize elements by category."""

    category_data = {}

    for category_name in selected_categories:

        category_id = CATEGORY_CONFIG[category_name]

        elements = collect_elements(
            document,
            category_id
        )

        category_data[category_name] = elements

    return category_data


# --------------------------------------------------
# 5. Generate collection report
# --------------------------------------------------

def generate_report(document, category_data):
    """Display element counts by category."""

    output.print_md("# BIM Quantity Extractor")
    output.print_md("## Multi-Category Collection Report")

    output.print_md(
        "**Model:** {}".format(document.Title)
    )

    output.print_md(
        "**Selected categories:** {}".format(
            len(category_data)
        )
    )

    total_elements = 0
    rows = []

    for category_name in CATEGORY_ORDER:

        if category_name not in category_data:
            continue

        elements = category_data[category_name]
        count = len(elements)

        total_elements += count

        if count == 0:
            status = "No elements found"
        else:
            status = "OK"

        rows.append([
            category_name,
            count,
            status
        ])

    output.print_md(
        "**Total elements:** {}".format(total_elements)
    )

    output.print_table(
        table_data=rows,
        columns=[
            "Category",
            "Element Count",
            "Status"
        ],
        title="Elements by Category"
    )

    output.print_md("## Extraction Notes")

    output.print_md(
        "- Only element instances are collected."
    )

    output.print_md(
        "- Element types are excluded."
    )

    output.print_md(
        "- Linked models are outside the current scope."
    )

    output.print_md(
        "- No model elements have been modified."
    )


# --------------------------------------------------
# 6. Main workflow
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

    category_data = collect_selected_categories(
        doc,
        selected_categories
    )

    generate_report(
        doc,
        category_data
    )


if __name__ == "__main__":
    main()
