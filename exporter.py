
import os
import copy
import bpy


export_path = r"C:\Users\rawmeat\Documents\GitHub\turret_gunner\Assets\Art"

selected = bpy.context.selected_objects
bpy.ops.object.select_all(action='DESELECT')

for obj in selected:
    original_location = copy.copy(obj.location)
    print(obj.type, obj.name)
    
    obj.location = (0,0,0)
    
    obj.select_set(True)
    
    file_path = os.path.join(export_path, f"{obj.name}.fbx")
    
    # in try/except because we always want the object back in it's location even if things fail
    try:
        bpy.ops.export_scene.fbx(filepath=file_path, use_selection=True, axis_up='Z')
    except Exception as e:
        print(e)
    
    obj.location = original_location
    obj.select_set(False)
    
    