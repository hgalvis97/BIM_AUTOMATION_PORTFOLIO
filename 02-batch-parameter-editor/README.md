# Batch Parameter Editor

**Project 02 — BIM Automation Portfolio**

A pyRevit tool for controlled batch editing of Autodesk Revit instance parameters using Python and the Revit API.

## Overview

The Batch Parameter Editor allows users to update supported instance text parameters across selected Revit elements.

The tool combines parameter validation, change previews, user confirmation, and Revit transactions to provide a controlled model-editing workflow.

## Technology Stack

- Autodesk Revit 2024.3
- pyRevit 7.1
- IronPython
- Autodesk Revit API
- Visual Studio Code
- Git and GitHub

## Features

### 1. Parameter Selection

Users can choose between:

- **Comments:** Batch editing of instance comments.
- **Mark:** Single-element editing to reduce accidental duplicate identifiers.
- **Custom Text Parameter:** Batch editing of compatible, uniquely named instance text parameters.

### 2. Parameter Validation

Before modifying elements, the tool checks:

- Whether the element is an instance rather than an element type.
- Whether the element belongs to a group.
- Parameter existence.
- Parameter storage type (`DB.StorageType.String`).
- Read-only status (`Parameter.IsReadOnly`).
- Whether the existing value already matches the requested value.
- Ambiguous parameter names for custom parameter selection.

Unsupported elements are skipped with an explanation.

### 3. Change Preview

Before committing changes, the tool displays:

- Selected parameter.
- Editable element count.
- Skipped element count.
- Current values.
- Proposed new values.

### 4. Controlled Model Modification

Changes are executed using a single `DB.Transaction`.

The implementation checks the transaction status and attempts rollback if an exception occurs during execution.

### 5. Execution Report

After execution, the tool reports:

- Transaction status.
- Updated elements.
- Skipped elements.
- Execution errors or warnings.

## Installation

1. Install Revit 2024 and a compatible pyRevit version.
2. Clone this repository.
3. Register the `02-batch-parameter-editor/src/` folder as a pyRevit extension search path.
4. Reload pyRevit.
5. Open the **VDC** tab.
6. Navigate to **Parameter Tools → Batch Editor**.

## Usage

1. Open an editable Revit project.
2. Select one or more elements.
3. Launch **Batch Editor**.
4. Choose a supported parameter.
5. Enter the new text value.
6. Review the proposed changes.
7. Confirm the operation.
8. Review the execution report.

## Testing and Validation

### Milestone 01 — Basic Batch Editing

Tested on a local copy of the Autodesk architectural sample model.

| Test | Result |
|---|---|
| Selected elements | 3 doors |
| Parameter | Comments |
| New value | QA TEST |
| Updated | 3 |
| Skipped | 0 |
| Transaction | Committed |
| Property verification | Passed |

### Milestone 02 — Transaction Rollback

A separate test command was implemented to simulate an execution failure and attempt to restore the original parameter value using `Transaction.RollBack()`.

The controlled test result should be recorded separately once verified.

### Milestone 03 — Enhanced Parameter Selection

Implemented parameter selection for Comments, Mark, and custom text parameters.

The enhanced interface has been launched and tested locally in Revit. Individual test outcomes should be documented with screenshots before final release.

## Screenshots

### Basic Batch Update

![Successful batch update](screenshots/01-successful-batch-update.png)

Additional screenshots will document parameter selection, Mark editing, and transaction rollback.

## Limitations

- Only text parameters are supported.
- Custom parameters must have an unambiguous name on each edited element.
- Custom-parameter selection does not yet use shared parameter GUIDs.
- Mark editing is restricted to one selected element but does not perform a model-wide uniqueness check.
- Empty replacement values are not supported.
- Workshared and linked model scenarios are not fully validated.
- A committed transaction is not a substitute for independent verification of model data.

## Development Approach

Development follows an iterative workflow:

**Build → Test → Commit → Document → Learn**

The first milestone prioritized a working MVP. Subsequent development expanded the parameter selection capabilities while retaining validation and transaction safeguards.

The final development review will explain the relevant Python concepts, Revit API methods, implementation decisions, and testing strategy.

## Project Status

**Enhanced functional prototype — final validation and documentation pending.**

## Portfolio

[Back to BIM Automation Portfolio](https://github.com/hgalvis97/BIM_AUTOMATION_PORTFOLIO)