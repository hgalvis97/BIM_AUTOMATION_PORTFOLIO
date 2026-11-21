
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
