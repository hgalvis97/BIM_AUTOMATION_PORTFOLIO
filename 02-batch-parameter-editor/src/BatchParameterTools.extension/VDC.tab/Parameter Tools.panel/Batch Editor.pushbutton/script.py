
# -*- coding: utf-8 -*-

"""
BATCH PARAMETER EDITOR
BIM Automation Portfolio - Project 02

Milestone 04:
- Automatic discovery of editable instance text parameters
- Common parameter detection across selected elements
- Built-in Comments batch editing
- Built-in Mark single-element editing
- Preview and confirmation
- Atomic transactions and rollback handling
- Detailed execution reporting

Environment: Revit 2024.3, pyRevit 7.1, IronPython
"""

from pyrevit import revit, DB, forms, script

COMMENTS_ID = DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS
MARK_ID = DB.BuiltInParameter.ALL_MODEL_MARK

def get_selected_elements(document, uidocument):
    """Return elements from the active Revit selection."""

    elements = []

    for element_id in uidocument.Selection.GetElementIds():
        element = document.GetElement(element_id)

        if element is not None:
            elements.append(element)

    return elements

def is_supported_instance(element):
    """Reject element types and grouped elements."""

    if isinstance(element, DB.ElementType):
        return False

    if element.GroupId != DB.ElementId.InvalidElementId:
        return False

    return True

def get_discoverable_parameters(element, document):
    """Return supported document-defined instance text parameters."""

    discovered = {}

    if not is_supported_instance(element):
        return discovered

    for parameter in element.Parameters:

        if parameter.StorageType != DB.StorageType.String:
            continue

        if parameter.IsReadOnly:
            continue

        parameter_id = parameter.Id.IntegerValue

        # Built-in parameters have negative IDs.
        # They are not offered through automatic discovery.
        if parameter_id <= 0:
            continue

        definition_element = document.GetElement(parameter.Id)

        # Only expose parameters with a document-level
        # ParameterElement definition.
        if not isinstance(definition_element, DB.ParameterElement):
            continue

        parameter_name = parameter.Definition.Name

        if parameter_name:
            discovered[parameter_id] = parameter_name

    return discovered

def discover_common_parameters(elements, document):
    """Find editable parameters common to all eligible instances."""

    eligible = [
        element for element in elements
        if is_supported_instance(element)
    ]

    if not eligible:
        return []

    common = get_discoverable_parameters(
        eligible[0], document
    )

    for element in eligible[1:]:

        current = get_discoverable_parameters(
            element, document
        )

        common_ids = set(common.keys()).intersection(
            set(current.keys())
        )

        common = {
            parameter_id: common[parameter_id]
            for parameter_id in common_ids
            if common[parameter_id] == current[parameter_id]
        }

    result = []

    for parameter_id, name in common.items():
        result.append({
            "name": name,
            "mode": "discovered",
            "id": parameter_id
        })

    return sorted(
        result,
        key=lambda item: (
            item["name"].lower(),
            item["id"]
        )
    )

def builtin_is_editable(element, builtin_id):
    """Check whether an instance built-in text parameter is writable."""

    if not is_supported_instance(element):
        return False

    parameter = element.get_Parameter(builtin_id)

    return (
        parameter is not None
        and parameter.StorageType == DB.StorageType.String
        and not parameter.IsReadOnly
    )

def choose_parameter(elements, document):
    """Build and display the available parameter choices."""

    eligible = [
        element for element in elements
        if is_supported_instance(element)
    ]

    if not eligible:
        forms.alert(
            "No supported instance elements were selected.",
            title="Batch Parameter Editor"
        )
        return None

    options = {}

    comments_available = all(
        builtin_is_editable(element, COMMENTS_ID)
        for element in eligible
    )

    if comments_available:
        label = "Comments [Built-in | Batch]"
        options[label] = {
            "name": "Comments",
            "mode": "builtin",
            "id": COMMENTS_ID
        }

    # Mark must be edited on exactly one selected instance.
    if len(elements) == 1 and builtin_is_editable(
        elements[0], MARK_ID
    ):
        label = "Mark [Built-in | Single element]"
        options[label] = {
            "name": "Mark",
            "mode": "builtin",
            "id": MARK_ID
        }

    discovered = discover_common_parameters(
        elements, document
    )

    for item in discovered:

        label = "{} [Parameter ID: {}]".format(
            item["name"],
            item["id"]
        )

        options[label] = item

    if not options:
        forms.alert(
            "No compatible editable text parameters were found.",
            title="Batch Parameter Editor"
        )
        return None

    selected = forms.SelectFromList.show(
        sorted(options.keys()),
        title="Batch Parameter Editor - Select Parameter",
        button_name="Continue",
        multiselect=False
    )

    if selected is None:
        return None

    return options[selected]

def get_target_parameter(element, config):
    """Resolve the exact target parameter on an instance."""

    if config["mode"] == "builtin":

        parameter = element.get_Parameter(config["id"])

        if parameter is None:
            return None, "Parameter not found"

        return parameter, None

    matches = []

    for parameter in element.Parameters:
        if parameter.Id.IntegerValue == config["id"]:
            matches.append(parameter)

    if len(matches) != 1:
        return None, "Missing or ambiguous parameter identity"

    parameter = matches[0]

    if parameter.Id.IntegerValue <= 0:
        return None, "Built-in parameter is not supported here"

    if parameter.Definition.Name != config["name"]:
        return None, "Parameter definition mismatch"

    definition_element = element.Document.GetElement(
        parameter.Id
    )

    if not isinstance(definition_element, DB.ParameterElement):
        return None, "Unsupported parameter definition"

    return parameter, None

def validate_element(element, config, new_value):
    """Validate an element and the selected parameter."""

    if not is_supported_instance(element):
        return None, "Unsupported instance or grouped element"

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
    """Separate editable and skipped elements."""

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
    """Show the proposed changes before execution."""

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

    if editable:

        rows = []

        for item in editable:
            rows.append([
                str(item["id"]),
                item["old_value"],
                new_value
            ])

        output.print_table(
            table_data=rows,
            columns=[
                "Element ID",
                "Current Value",
                "Proposed Value"
            ]
        )

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

def apply_batch(document, editable, new_value):
    """Apply edits using one Revit transaction."""

    transaction = DB.Transaction(
        document, "Batch Parameter Editor"
    )

    try:
        start_status = transaction.Start()

        if start_status != DB.TransactionStatus.Started:
            raise Exception("Transaction could not be started")

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
    """Report the final transaction outcome."""

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
            "**SUCCESS:** Batch changes were committed."
        )

    elif status == "RolledBack":
        output.print_md(
            "**ROLLED BACK:** The transaction was reverted."
        )

    else:
        output.print_md(
            "**WARNING:** Transaction outcome is unverified. "
            "Inspect the model before continuing."
        )

    if error:
        output.print_md(
            "**Details:** {}".format(error)
        )

def main():
    """Run the parameter discovery and editing workflow."""

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

    config = choose_parameter(elements, doc)

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
        "Editable elements: {}\n"
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