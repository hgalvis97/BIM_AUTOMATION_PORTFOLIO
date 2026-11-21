
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
