
# -*- coding: utf-8 -*-

"""
BATCH PARAMETER EDITOR
Project: BIM Automation Portfolio - Project 02
Environment: Revit 2024 + pyRevit 7.1 + IronPython

MVP:
- Edit instance Comments on selected elements
- Validate parameters before editing
- Preview proposed changes
- Apply changes in one atomic transaction
- Roll back the batch on failure
- Report updated and skipped elements
"""

from pyrevit import revit, DB, forms, script


PARAMETER_ID = DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS
PARAMETER_NAME = "Comments"


def get_selected_elements(document, uidocument):
    """Return valid elements from the current Revit selection."""

    elements = []

    for element_id in uidocument.Selection.GetElementIds():
        element = document.GetElement(element_id)

        if element is not None:
            elements.append(element)

    return elements


def validate_element(element, new_value):
    """Check whether an element can receive the new text."""

    if isinstance(element, DB.ElementType):
        return None, "Element type is not supported"

    if element.GroupId != DB.ElementId.InvalidElementId:
        return None, "Element belongs to a group"

    parameter = element.get_Parameter(PARAMETER_ID)

    if parameter is None:
        return None, "Comments parameter not found"

    if parameter.StorageType != DB.StorageType.String:
        return None, "Parameter is not a text parameter"

    if parameter.IsReadOnly:
        return None, "Parameter is read-only"

    current_value = parameter.AsString() or ""

    if current_value == new_value:
        return None, "Value already matches"

    return parameter, None


def prepare_batch(elements, new_value):
    """Separate editable elements from skipped elements."""

    editable = []
    skipped = []

    for element in elements:
        parameter, reason = validate_element(
            element, new_value
        )

        if reason is not None:
            skipped.append({
                "id": element.Id,
                "reason": reason
            })
        else:
            editable.append({
                "id": element.Id,
                "parameter": parameter,
                "old_value": parameter.AsString() or ""
            })

    return editable, skipped


def print_preview(output, document, editable, skipped,
                  new_value):
    """Display the proposed batch before modification."""

    output.print_md("# Batch Parameter Editor")
    output.print_md("**Model:** {}".format(document.Title))
    output.print_md("**Parameter:** {}".format(PARAMETER_NAME))

    output.print_md("## Preview")

    output.print_table(
        table_data=[
            ["Editable elements", len(editable)],
            ["Skipped elements", len(skipped)],
            ["New value", new_value]
        ],
        columns=["Metric", "Value"]
    )

    rows = []

    for item in editable:
        rows.append([
            str(item["id"]),
            item["old_value"],
            new_value
        ])

    if rows:
        output.print_table(
            table_data=rows,
            columns=["Element ID", "Old Value", "New Value"]
        )


def apply_batch(document, editable, new_value):
    """Apply all edits in one atomic Revit transaction."""

    transaction = DB.Transaction(
        document, "Batch Parameter Editor"
    )

    try:
        transaction.Start()

        for item in editable:
            success = item["parameter"].Set(new_value)

            if not success:
                raise Exception(
                    "Parameter.Set failed for element {}".format(
                        item["id"]
                    )
                )

        status = transaction.Commit()

        if status != DB.TransactionStatus.Committed:
            raise Exception(
                "Transaction was not committed. Status: {}".format(
                    status
                )
            )

        return True, None

    except Exception as error:
        try:
            if transaction.GetStatus() == DB.TransactionStatus.Started:
                transaction.RollBack()
        except Exception as rollback_error:
            return False, (
                "{} | Rollback error: {}".format(
                    error, rollback_error
                )
            )

        return False, str(error)


def print_results(output, editable, skipped, success, error):
    """Print the final batch execution report."""

    output.print_md("## Execution Results")

    updated_count = len(editable) if success else 0

    output.print_table(
        table_data=[
            ["Status", "Committed" if success else "Not committed"],
            ["Updated", updated_count],
            ["Skipped", len(skipped)]
        ],
        columns=["Metric", "Result"]
    )

    if success:
        output.print_md(
            "**SUCCESS:** Batch changes were committed."
        )

    else:
        output.print_md(
            "**FAILED:** No successful commit was recorded."
        )
        output.print_md("**Error:** {}".format(error))

    if skipped:
        output.print_md("## Skipped Elements")

        rows = []

        for item in skipped:
            rows.append([
                str(item["id"]),
                item["reason"]
            ])

        output.print_table(
            table_data=rows,
            columns=["Element ID", "Reason"]
        )


def main():
    """Execute the batch parameter editing workflow."""

    doc = revit.doc
    uidoc = revit.uidoc

    output = script.get_output()
    output.set_title("Batch Parameter Editor")

    if doc is None or uidoc is None:
        forms.alert(
            "No active Revit document was found.",
            exitscript=True
        )
        return

    if doc.IsFamilyDocument:
        forms.alert(
            "Open a Revit project document to use this tool.",
            exitscript=True
        )
        return

    if doc.IsReadOnly:
        forms.alert(
            "The active document is read-only.",
            exitscript=True
        )
        return

    elements = get_selected_elements(doc, uidoc)

    if not elements:
        forms.alert(
            "Select one or more elements before running the tool.",
            exitscript=True
        )
        return

    new_value = forms.ask_for_string(
        default="",
        prompt="Enter the new instance Comments value:",
        title="Batch Parameter Editor"
    )

    if new_value is None:
        return

    if not new_value.strip():
        forms.alert(
            "The new value cannot be empty.",
            exitscript=True
        )
        return

    editable, skipped = prepare_batch(
        elements, new_value
    )

    print_preview(
        output, doc, editable, skipped, new_value
    )

    if not editable:
        forms.alert(
            "No editable elements were found.",
            exitscript=True
        )
        return

    confirmed = forms.alert(
        "Update Comments on {} elements?\n\n"
        "Skipped elements: {}\n\n"
        "Review the preview before confirming.".format(
            len(editable),
            len(skipped)
        ),
        title="Confirm Batch Update",
        yes=True,
        no=True
    )

    if not confirmed:
        output.print_md(
            "## Cancelled - No changes were made."
        )
        return

    success, error = apply_batch(
        doc, editable, new_value
    )

    print_results(
        output, editable, skipped, success, error
    )

    if success:
        forms.alert(
            "Batch update completed.\n\n"
            "Updated: {}\n"
            "Skipped: {}".format(
                len(editable), len(skipped)
            ),
            title="Batch Parameter Editor"
        )

    else:
        forms.alert(
            "Batch update failed.\n"
            "No successful commit was recorded.\n\n"
            "Review the pyRevit output for details.",
            title="Batch Parameter Editor"
        )


if __name__ == "__main__":
    main()
