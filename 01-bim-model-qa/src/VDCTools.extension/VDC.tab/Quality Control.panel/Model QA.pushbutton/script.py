
from pyrevit import revit, DB

# Access the active Revit document
doc = revit.doc

# Collect all door instances
collector = DB.FilteredElementCollector(doc)

doors = list(
    collector
    .OfCategory(DB.BuiltInCategory.OST_Doors)
    .WhereElementIsNotElementType()
)

# Display results
print("Model: {}".format(doc.Title))
print("Total doors: {}".format(len(doors)))


# Inspect individual door elements
for door in doors:
    print("Element ID: {}".format(door.Id))
    print("Name: {}".format(door.Name))
    print("-------------------------")
    # Get the Mark instance parameter
    mark_param = door.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
    mark = mark_param.AsString() if mark_param else None
    print("Mark: {}".format(mark))


# Explore all instance parameters of the first door
if doors:
    first_door = doors[0]

    print("\nINSTANCE PARAMETER EXPLORER")
    print("Element ID: {}".format(first_door.Id))

    for param in first_door.Parameters:
        print("{} | {}".format(
            param.Definition.Name,
            param.StorageType
        ))

# Explore type parameters
if doors:
    first_door = doors[0]

    type_id = first_door.GetTypeId()
    door_type = doc.GetElement(type_id)

    if door_type:
        print("\nTYPE PARAMETER EXPLORER")
        print("Type ID: {}".format(type_id))

        for param in door_type.Parameters:
            print("{} | {}".format(
                param.Definition.Name,
                param.StorageType
            ))

# Extract door dimensions
print("\nDOOR DIMENSION EXPLORER")

for door in doors:

    # Get the door type
    door_type = doc.GetElement(door.GetTypeId())

    if not door_type:
        continue

    # Get dimension parameters
    width_param = door_type.get_Parameter(
        DB.BuiltInParameter.DOOR_WIDTH
    )

    height_param = door_type.get_Parameter(
        DB.BuiltInParameter.DOOR_HEIGHT
    )

    # Display element information
    print("-------------------------")
    print("Element ID: {}".format(door.Id))
    print("Type: {}".format(door.Name))

    # Convert width to millimeters
    if width_param and width_param.HasValue:
        width_ft = width_param.AsDouble()

        width_mm = DB.UnitUtils.ConvertFromInternalUnits(
            width_ft,
            DB.UnitTypeId.Millimeters
        )

        print("Width: {:.2f} mm".format(width_mm))
    else:
        print("Width: Not available")

    # Convert height to millimeters
    if height_param and height_param.HasValue:
        height_ft = height_param.AsDouble()

        height_mm = DB.UnitUtils.ConvertFromInternalUnits(
            height_ft,
            DB.UnitTypeId.Millimeters
        )

        print("Height: {:.2f} mm".format(height_mm))
    else:
        print("Height: Not available")

