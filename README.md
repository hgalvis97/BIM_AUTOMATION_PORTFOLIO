# BIM Model QA Checker

**Automated BIM Quality Control using Python, pyRevit, and the Autodesk Revit API**

![Duplicate Mark Detection](screenshots/14-duplicate-mark-detection.png)

## 1. Project Overview

BIM Model QA Checker is a custom pyRevit extension designed to automate basic quality assurance checks on architectural door elements in Autodesk Revit.

The tool extracts BIM element information, applies predefined validation rules, and generates an interactive report directly inside Revit.

This project demonstrates practical knowledge of Python, the Revit API, BIM data structures, and automation workflows used in Architecture, Engineering, and Construction (AEC).

**Project Type:** BIM Automation / Quality Assurance  
**Software:** Autodesk Revit 2024  
**Development Environment:** Visual Studio Code  
**Technologies:** Python, IronPython, pyRevit, Autodesk Revit API  
**Status:** Functional prototype — tested in Revit 2024

## 2. Problem Statement

BIM models contain large amounts of structured information that must remain accurate and consistent throughout the project lifecycle.

Manually reviewing element parameters can be time-consuming, particularly in larger models.

Common data quality concerns include:

- Missing element identification values.
- Duplicate door identification marks.
- Unavailable dimensional information.
- Invalid numerical parameter values.

BIM Model QA Checker automates an initial review of these conditions and provides a structured report to support further model inspection.

## 3. Features

### Automated Door Data Extraction

Uses `FilteredElementCollector` to retrieve door instances from the active Revit document.

The tool extracts:

| Parameter | Description |
|---|---|
| Element ID | Unique identifier within the Revit document |
| Type ID | Reference to the associated door type |
| Mark | Instance identification parameter |
| Type Name | Name of the associated door type |
| Width | Door width converted to millimeters |
| Height | Door height converted to millimeters |

### BIM Quality Validation

Four quality assurance rules are implemented:

| Rule | Severity | Description |
|---|---|---|
| Missing Mark | ERROR | Identifies doors with empty or missing Mark values |
| Duplicate Mark | WARNING | Detects repeated Mark values across door instances |
| Missing Dimensions | REVIEW | Flags dimensions unavailable through the queried parameters |
| Invalid Dimensions | ERROR | Identifies zero or negative width or height values |

Duplicate Mark detection uses normalized strings to account for differences in capitalization and surrounding spaces.

**Note:** Duplicate marks may be acceptable depending on project naming conventions. Likewise, missing dimension parameter values do not necessarily indicate missing physical geometry.

### Interactive QA Report

The tool generates a report containing:

- Model identification and door inventory.
- Total findings grouped by severity.
- Tabulated door information.
- Quality assurance findings.
- Clickable element links for locating issues in Revit.

The tool performs read-only operations and does not modify the BIM model.

## 4. Technical Architecture

The application follows a modular workflow:

```text
Autodesk Revit Model
        |
        v
collect_doors()
        |
        v
extract_door_data()
        |
        v
validate_doors()
        |
        v
generate_report()
        |
        v
Interactive pyRevit Output
```

### Main Functions

| Function | Responsibility |
|---|---|
| `collect_doors()` | Retrieves door instances using the Revit API |
| `get_string_parameter()` | Safely retrieves text parameters |
| `get_dimension_mm()` | Reads length parameters and converts internal units |
| `extract_door_data()` | Converts Revit elements into structured Python dictionaries |
| `validate_doors()` | Executes BIM quality validation rules |
| `get_severity_counts()` | Aggregates findings by severity |
| `generate_report()` | Produces formatted tables and interactive element links |
| `main()` | Coordinates execution |

### Key Technical Concepts

**Revit API integration:** Uses `Autodesk.Revit.DB` classes through pyRevit to access document elements and parameters.

**Instance and type parameters:** Retrieves instance-specific values such as Mark and shared type parameters such as door dimensions.

**Unit conversion:** Uses `UnitUtils.ConvertFromInternalUnits()` to convert Revit internal length units into millimeters.

**Structured data processing:** Stores extracted element data in Python dictionaries and applies validation rules without repeatedly querying the Revit model.

**IronPython compatibility:** Uses Python syntax compatible with the configured IronPython environment, including `.format()` for string formatting.

## 5. Repository Structure

```text
01-bim-model-qa/
|
|-- src/
|   |-- VDCTools.extension/
|       |-- VDC.tab/
|           |-- Quality Control.panel/
|               |-- Model QA.pushbutton/
|                   |-- script.py
|                   |-- icon.png
|
|-- screenshots/
|-- sample-model/
|-- docs/
|-- README.md
```

The Autodesk Revit sample model is maintained locally and excluded from version control using `.gitignore`.

## 6. Installation

### Requirements

- Autodesk Revit 2024 (tested with Revit 2024.3).
- pyRevit installed and attached to Revit.
- Windows operating system.
- An architectural Revit model containing door elements.

### Setup Instructions

1. Clone or download this repository.
2. Open Autodesk Revit.
3. Navigate to the pyRevit settings.
4. Add the directory containing `VDCTools.extension` to **Custom Extension Directories**. For this repository, that directory is `01-bim-model-qa/src`.
5. Save the configuration and reload pyRevit.
6. Locate the new **VDC** tab.
7. Open a Revit project and click **Model QA** in the **Quality Control** panel.

The tool automatically analyzes door elements in the active document.

## 7. Testing and Results

The prototype was developed and tested using Autodesk's architectural sample project in Revit 2024.

### Test Environment

| Property | Result |
|---|---|
| Revit Version | 2024.3 |
| pyRevit Version | 7.1 |
| Model | Autodesk architectural sample project |
| Door Instances | 16 |
| Available Door Types | 5 |
| Used Door Types | 5 |

### Test 1 — Missing Mark Detection

A door Mark value was temporarily cleared in a separate test copy of the model.

**Result:** The validation function successfully identified the missing value and generated an ERROR finding.

### Test 2 — Duplicate Mark Detection

Two door instances were assigned the same Mark value, `206A`.

**Result:** The tool successfully generated WARNING findings for both affected elements.

![Duplicate Mark Validation](screenshots/14-duplicate-mark-detection.png)

### Test 3 — Interactive Issue Navigation

The QA report generated interactive element references through pyRevit's output functionality, enabling users to locate affected elements.

### Testing Scope

Missing Mark and Duplicate Mark detection were verified through controlled model changes.

Dimension extraction was tested across multiple door types. Missing Dimensions and Invalid Dimensions remain implemented validation rules, but require additional targeted testing before being considered fully verified.

## 8. Limitations

This project is an initial proof of concept and has the following limitations:

- Only the Doors category is currently analyzed.
- Duplicate Mark validation does not distinguish between building levels, phases, or project-specific naming conventions.
- Some door families may store dimensions in custom parameters or geometry not covered by the current extraction methods.
- Missing parameter values do not necessarily indicate invalid model geometry.
- The current report is displayed inside pyRevit and is not yet exported to Excel, CSV, or external reporting systems.
- Automated regression testing is not yet implemented.

The tool is intended to support BIM quality review, not replace project-specific BIM standards or professional model coordination.

## 9. Future Improvements

Potential enhancements include:

- Support for Rooms, Windows, Walls, and additional BIM categories.
- Configurable QA rules and severity levels.
- Improved dimensional parameter detection.
- CSV and Excel report exports.
- Model quality indicators and aggregated dashboards.
- Automated tests for validation functions.
- Integration with BIM coordination and data analytics workflows.

## 10. Skills Demonstrated

This project demonstrates foundational competencies in:

- BIM data extraction and validation.
- Autodesk Revit API programming.
- pyRevit extension development.
- Python functions and data structures.
- Object-oriented API navigation.
- Parameter and unit handling.
- Defensive programming and error handling.
- Debugging IronPython integration issues.
- Git version control and iterative development.
- Technical documentation.

## 11. References

- [Autodesk Revit API Documentation](https://www.revitapidocs.com/2024/)
- [pyRevit Documentation](https://docs.pyrevitlabs.io/)
- [pyRevit GitHub Repository](https://github.com/pyrevitlabs/pyRevit)
- [Autodesk Revit Sample Project Files](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-GetStarted/files/GUID-61EF2F22-3A1F-4317-B925-1E85F138BE88.htm)

---

**BIM Automation Portfolio — Project 01**

*Exploring practical applications of Python, BIM data, and automation in the AEC industry.*
