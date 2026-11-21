
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
