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


def main():

    # Step 1: Collect door instances
    doors = collect_doors(doc)

    # Step 2: Extract structured door data
    all_door_data = []

    for door in doors:
        data = extract_door_data(door, doc)
        all_door_data.append(data)

    # Step 3: Display extraction results
    print("BIM MODEL QA - DATA EXTRACTION")
    print("Model: {}".format(doc.Title))
    print("Total doors: {}".format(len(all_door_data)))

    for data in all_door_data:

        print("---------------------------")
        print("Element ID: {}".format(data["element_id"]))
        print("Mark: {}".format(data["mark"]))
        print("Type: {}".format(data["type_name"]))

        width = data["width_mm"]
        height = data["height_mm"]

        if width is not None:
            print("Width: {:.2f} mm".format(width))
        else:
            print("Width: Not available")

        if height is not None:
            print("Height: {:.2f} mm".format(height))
        else:
            print("Height: Not available")

if __name__ == "__main__":
    main()

    


