
# -*- coding: utf-8 -*-

"""
BATCH PARAMETER EDITOR
BIM Automation Portfolio - Project 02

Features:
- Built-in Comments batch editing
- Built-in Mark single-element editing
- Custom instance text parameter editing
- Parameter validation and change preview
- User confirmation
- Atomic Revit transaction
- Rollback attempt on execution failure
- Detailed execution report

Environment: Revit 2024.3, pyRevit 7.1, IronPython
"""

from pyrevit import revit, DB, forms, script

PARAMETER_OPTIONS = [
    "Comments - Batch editing",
    "Mark - Single element",
    "Custom text parameter - Batch editing"
]

def get_selected_elements(document, uidocument):
    """Collect elements from the active Revit selection."""

    elements = []

    for element_id in uidocument.Selection.GetElementIds():
        element = document.GetElement(element_id)

        if element is not None:
            elements.append(element)

    return elements

def choose_parameter(elements):
    """Ask the user which instance text parameter to edit."""

    selected = forms.SelectFromList.show(
        PARAMETER_OPTIONS,
        title="Batch Parameter Editor - Select Parameter",
        button_name="Continue",
        multiselect=False
    )

    if selected is None:
        return None

    if selected == PARAMETER_OPTIONS[0]:
        return {
            "name": "Comments",
            "mode": "builtin",
            "id": DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS
        }

    if selected == PARAMETER_OPTIONS[1]:

        if len(elements) != 1:
            forms.alert(
                "Mark editing is restricted to one selected "
                "element at a time.",
                title="Batch Parameter Editor"
            )
            return None

        return {
            "name": "Mark",
            "mode": "builtin",
            "id": DB.BuiltInParameter.ALL_MODEL_MARK
        }

    if selected == PARAMETER_OPTIONS[2]:

        parameter_name = forms.ask_for_string(
            default="",
            prompt="Enter the exact instance parameter name:",
            title="Custom Text Parameter"
        )

        if parameter_name is None:
            return None

        parameter_name = parameter_name.strip()

        if not parameter_name:
            forms.alert(
                "Parameter name cannot be empty.",
                title="Batch Parameter Editor"
            )
            return None

        return {
            "name": parameter_name,
            "mode": "custom",
            "id": None
        }

    return None

def get_target_parameter(element, config):
    """Resolve a supported instance parameter."""

    if config["mode"] == "builtin":
        parameter = element.get_Parameter(config["id"])

        if parameter is None:
            return None, "Parameter not found"

        return parameter, None

    # GetParameters returns all parameters matching this name.
    # Reject ambiguous matches rather than editing the wrong one.
    parameters = list(
        element.GetParameters(config["name"])
    )

    if len(parameters) == 0:
        return None, "Custom parameter not found"

    if len(parameters) > 1:
        return None, "Ambiguous parameter name"

    parameter = parameters[0]

    # Built-in parameters must be selected explicitly.
    # This prevents bypassing the single-element Mark rule.
    if parameter.Id.IntegerValue < 0:
        return None, "Use the built-in parameter option"

    return parameter, None

def validate_element(element, config, new_value):
    """Validate one element before modification."""

    if isinstance(element, DB.ElementType):
        return None, "Element type is not supported"

    if element.GroupId != DB.ElementId.InvalidElementId:
        return None, "Element belongs to a group"

    parameter, reason = get_target_parameter(
        element, config
    )

    if reason is not None:
        return None, reason

    if parameter.StorageType != DB.StorageType.String:
        return None, "Parameter is not a text parameter"

    if parameter.IsReadOnly:
        return None, "Parameter is read-only"

    current_value = parameter.AsString() or ""

    if current_value == new_value:
        return None, "Value already matches"

    return parameter, None

def prepare_batch(elements, config, new_value):
    """Build editable and skipped element lists."""

    editable = []
    skipped = []

    for element in elements:

        parameter, reason = validate_element(
            element, config, new_value
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

def print_preview(output, document, config,
                  editable, skipped, new_value):
    """Display changes before the transaction."""

    output.print_md("# Batch Parameter Editor")
    output.print_md(
        "**Model:** {}".format(document.Title)
    )
    output.print_md(
        "**Parameter:** {}".format(config["name"])
    )

    output.print_md("## Change Preview")

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
            columns=[
                "Element ID",
                "Current Value",
                "Proposed Value"
            ]
        )

    if skipped:
        output.print_md("## Pre-validation Skips")

        skipped_rows = []

        for item in skipped:
            skipped_rows.append([
                str(item["id"]),
                item["reason"]
            ])

        output.print_table(
            table_data=skipped_rows,
            columns=["Element ID", "Reason"]
        )

def apply_batch(document, editable, new_value):
    """Execute all edits in a single transaction."""

    transaction = DB.Transaction(
        document, "Batch Parameter Editor"
    )

    try:
        start_status = transaction.Start()

        if start_status != DB.TransactionStatus.Started:
            raise Exception(
                "Transaction could not be started."
            )

        for item in editable:

            success = item["parameter"].Set(new_value)

            if not success:
                raise Exception(
                    "Parameter.Set failed for element {}".format(
                        item["id"]
                    )
                )

        commit_status = transaction.Commit()

        if commit_status != DB.TransactionStatus.Committed:
            raise Exception(
                "Transaction did not commit: {}".format(
                    commit_status
                )
            )

        return "Committed", None

    except Exception as error:

        message = str(error)

        try:
            status = transaction.GetStatus()

            if status == DB.TransactionStatus.Started:
                rollback_status = transaction.RollBack()

                if rollback_status == DB.TransactionStatus.RolledBack:
                    return "RolledBack", message

                return (
                    "Unverified",
                    "{} | Rollback status: {}".format(
                        message, rollback_status
                    )
                )

            if status == DB.TransactionStatus.RolledBack:
                return "RolledBack", message

            return (
                "Unverified",
                "{} | Transaction status: {}".format(
                    message, status
                )
            )

        except Exception as rollback_error:
            return (
                "Unverified",
                "{} | Rollback error: {}".format(
                    message, rollback_error
                )
            )

def print_results(output, editable, skipped,
                  status, error):
    """Show transaction outcome and element counts."""

    output.print_md("## Execution Results")

    committed = status == "Committed"

    output.print_table(
        table_data=[
            ["Transaction", status],
            [
                "Updated",
                len(editable) if committed else 0
            ],
            ["Skipped", len(skipped)]
        ],
        columns=["Metric", "Result"]
    )

    if committed:
        output.print_md(
            "**SUCCESS:** Changes were committed."
        )

    elif status == "RolledBack":
        output.print_md(
            "**ROLLED BACK:** No batch changes were committed."
        )

    else:
        output.print_md(
            "**WARNING:** Transaction outcome could "
            "not be fully verified. Inspect the model."
        )

    if error is not None:
        output.print_md(
            "**Details:** {}".format(error)
        )

def main():
    """Run the Batch Parameter Editor."""

    doc = revit.doc
    uidoc = revit.uidoc

    output = script.get_output()
    output.set_title("Batch Parameter Editor")

    if doc is None or uidoc is None:
        forms.alert(
            "No active Revit project.",
            exitscript=True
        )
        return

    if doc.IsFamilyDocument or doc.IsReadOnly:
        forms.alert(
            "Open an editable Revit project document.",
            exitscript=True
        )
        return

    elements = get_selected_elements(doc, uidoc)

    if not elements:
        forms.alert(
            "Select one or more elements first.",
            exitscript=True
        )
        return

    config = choose_parameter(elements)

    if config is None:
        return

    new_value = forms.ask_for_string(
        default="",
        prompt="Enter the new value for {}:".format(
            config["name"]
        ),
        title="Batch Parameter Editor"
    )

    if new_value is None:
        return

    if not new_value.strip():
        forms.alert(
            "Value cannot be empty.",
            exitscript=True
        )
        return

    editable, skipped = prepare_batch(
        elements, config, new_value
    )

    print_preview(
        output, doc, config,
        editable, skipped, new_value
    )

    if not editable:
        forms.alert(
            "No editable elements found.",
            exitscript=True
        )
        return

    confirmed = forms.alert(
        "Parameter: {}\n"
        "Eligible elements: {}\n"
        "Skipped elements: {}\n\n"
        "Apply these changes?".format(
            config["name"],
            len(editable),
            len(skipped)
        ),
        title="Confirm Batch Update",
        yes=True,
        no=True
    )

    if not confirmed:
        output.print_md(
            "## Cancelled - No changes made."
        )
        return

    status, error = apply_batch(
        doc, editable, new_value
    )

    print_results(
        output, editable, skipped,
        status, error
    )

    if status == "Committed":
        forms.alert(
            "Batch update completed.\n\n"
            "Updated: {}\n"
            "Skipped: {}".format(
                len(editable),
                len(skipped)
            ),
            title="Batch Parameter Editor"
        )

    elif status == "RolledBack":
        forms.alert(
            "Transaction rolled back.\n"
            "Review the output for details.",
            title="Batch Parameter Editor"
        )

    else:
        forms.alert(
            "Transaction outcome is unverified.\n"
            "Inspect the model before continuing.",
            title="Batch Parameter Editor"
        )

if __name__ == "__main__":
    main()