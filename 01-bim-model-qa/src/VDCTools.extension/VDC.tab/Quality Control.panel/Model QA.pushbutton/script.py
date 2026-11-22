from pyrevit import revit, DB

doc = revit.doc


# Collect door instances from the active document
def collect_doors(document):

    collector = DB.FilteredElementCollector(document)

    doors = list(
        collector
        .OfCategory(DB.BuiltInCategory.OST_Doors)
        .WhereElementIsNotElementType()
    )

    return doors


# Read a text parameter from a Revit element
def get_string_parameter(element, parameter_id):

    param = element.get_Parameter(parameter_id)

    if not param:
        return None

    if not param.HasValue:
        return None

    if param.StorageType != DB.StorageType.String:
        return None

    return param.AsString()


# Read a length parameter and convert it to millimeters
def get_dimension_mm(element, parameter_id):

    param = element.get_Parameter(parameter_id)

    if not param:
        return None

    if not param.HasValue:
        return None

    if param.StorageType != DB.StorageType.Double:
        return None

    value_internal = param.AsDouble()

    value_mm = DB.UnitUtils.ConvertFromInternalUnits(
        value_internal,
        DB.UnitTypeId.Millimeters
    )

    return value_mm

# Extract structured data from a door instance
def extract_door_data(door, document):

    # Get the door type
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

    # Type parameters
    if door_type:

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

    # Store extracted information
    door_data = {
        "element_id": door.Id,
        "type_id": type_id,
        "mark": mark,
        "type_name": type_name,
        "width_mm": width_mm,
        "height_mm": height_mm
    }

    return door_data


# Validate door data against BIM quality rules
def validate_doors(all_door_data):

    issues = []

    for door_data in all_door_data:

        element_id = door_data["element_id"]
        mark = door_data["mark"]

        # Rule 01: Missing Door Mark
        if mark is None or not mark.strip():

            issue = {
                "element_id": element_id,
                "rule": "Missing Mark",
                "severity": "ERROR",
                "description": "Door Mark is empty or missing"
            }

            issues.append(issue)

    return issues



def main():

    # Step 1: Collect door instances
    doors = collect_doors(doc)

    # Step 2: Extract structured data
    all_door_data = []

    for door in doors:
        data = extract_door_data(door, doc)
        all_door_data.append(data)

    # Step 3: Validate door data
    issues = validate_doors(all_door_data)

    # Step 4: Display validation results
    print("BIM MODEL QA - VALIDATION REPORT")
    print("Model: {}".format(doc.Title))
    print("Total doors: {}".format(len(all_door_data)))
    print("Total issues: {}".format(len(issues)))

    print("\nQA ISSUES")

    if not issues:
        print("PASS - No missing Mark issues found.")

    else:
        for issue in issues:
            print("-------------------------")
            print("Element ID: {}".format(
                issue["element_id"]
            ))
            print("Rule: {}".format(
                issue["rule"]
            ))
            print("Severity: {}".format(
                issue["severity"]
            ))
            print("Description: {}".format(
                issue["description"]
            ))


if __name__ == "__main__":
    main()




    


