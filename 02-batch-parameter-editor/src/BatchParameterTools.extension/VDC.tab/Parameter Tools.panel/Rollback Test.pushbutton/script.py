
# -*- coding: utf-8 -*-

"""
CONTROLLED TRANSACTION ROLLBACK TEST
Project: BIM Automation Portfolio - Project 02

Test:
1. Read the original Comments value.
2. Start a Revit transaction.
3. Apply a temporary value.
4. Simulate a failure.
5. Roll back the transaction.
6. Verify that the original value was restored.
"""

from pyrevit import revit, DB, forms, script


TEST_VALUE = "TEMPORARY_ROLLBACK_TEST"


def main():

    doc = revit.doc
    uidoc = revit.uidoc

    output = script.get_output()
    output.set_title("Transaction Rollback Test")

    selected_ids = list(
        uidoc.Selection.GetElementIds()
    )

    if len(selected_ids) != 1:
        forms.alert(
            "Select exactly one test element.",
            exitscript=True
        )
        return

    element = doc.GetElement(selected_ids[0])

    if element is None:
        forms.alert(
            "Selected element was not found.",
            exitscript=True
        )
        return

    if isinstance(element, DB.ElementType):
        forms.alert(
            "Select an instance, not an element type.",
            exitscript=True
        )
        return

    if element.GroupId != DB.ElementId.InvalidElementId:
        forms.alert(
            "Grouped elements are not supported.",
            exitscript=True
        )
        return

    parameter = element.get_Parameter(
        DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS
    )

    if parameter is None:
        forms.alert(
            "Comments parameter not found.",
            exitscript=True
        )
        return

    if parameter.IsReadOnly:
        forms.alert(
            "Comments parameter is read-only.",
            exitscript=True
        )
        return

    if parameter.StorageType != DB.StorageType.String:
        forms.alert(
            "Comments parameter is not a string.",
            exitscript=True
        )
        return

    original_value = parameter.AsString() or ""

    confirmed = forms.alert(
        "Run a controlled rollback test?\n\n"
        "The tool will temporarily change Comments, "
        "simulate an error, and attempt to restore "
        "the original value.\n\n"
        "Use a disposable test model only.",
        title="Rollback Test",
        yes=True,
        no=True
    )

    if not confirmed:
        return

    transaction = DB.Transaction(
        doc, "Controlled Rollback Test"
    )

    rollback_status = None
    failure_message = None

    try:
        transaction.Start()

        success = parameter.Set(TEST_VALUE)

        if not success:
            raise Exception(
                "Temporary parameter update failed."
            )

        # Intentionally simulate a runtime failure.
        raise Exception(
            "SIMULATED FAILURE: Testing transaction rollback."
        )

    except Exception as error:
        failure_message = str(error)

        if transaction.GetStatus() == DB.TransactionStatus.Started:
            try:
                rollback_status = transaction.RollBack()
            except Exception as rollback_error:
                failure_message += (
                    " | Rollback error: {}".format(
                        rollback_error
                    )
                )

    current_parameter = element.get_Parameter(
        DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS
    )

    current_value = (
        current_parameter.AsString() or ""
        if current_parameter is not None
        else None
    )

    rollback_verified = (
        rollback_status == DB.TransactionStatus.RolledBack
        and current_value == original_value
    )

    output.print_md("# Controlled Rollback Test")

    output.print_table(
        table_data=[
            ["Element ID", str(element.Id)],
            ["Original value", original_value],
            ["Temporary value", TEST_VALUE],
            ["Final value", str(current_value)],
            ["Rollback status", str(rollback_status)],
            [
                "Verification",
                "PASS" if rollback_verified else "FAIL"
            ]
        ],
        columns=["Metric", "Result"]
    )

    output.print_md(
        "**Simulated error:** {}".format(failure_message)
    )

    if rollback_verified:
        forms.alert(
            "PASS: Rollback completed and the original "
            "Comments value was restored.",
            title="Rollback Test"
        )
    else:
        forms.alert(
            "FAIL: Rollback could not be verified. "
            "Inspect the model and output before continuing.",
            title="Rollback Test"
        )


if __name__ == "__main__":
    main()
