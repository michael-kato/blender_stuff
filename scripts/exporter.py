
import os
import copy
import bpy


export_path = r"C:\Users\rawmeat\Documents\Unreal Projects\gunship\Content\Model\export"

def export():
    
    # TODO: just put in object 
    bpy.ops.object.mode_set(mode='OBJECT')
    
    selected = bpy.context.selected_objects
    bpy.ops.object.select_all(action='DESELECT')

    for obj in selected:
        original_location = copy.copy(obj.location)
        print(obj.type, obj.name)
        
        obj.location = (0,0,0)
        
        obj.select_set(True)
        
        
        # Recursively select all children
        def select_children_recursive(parent_obj):
            for child in parent_obj.children:
                child.select_set(True)
                select_children_recursive(child)
        
        # Call the recursive function to select all children
        select_children_recursive(obj)
        
        
        file_path = os.path.join(export_path, f"{obj.name}.fbx")
        
        try:
            bpy.ops.export_scene.fbx(
                filepath=file_path, 
                use_selection=True, 
                export_smoothing_groups=True,
                batch_mode='OFF')
        except Exception as e:
            print(e)
        
        obj.location = original_location
        
        # deselect 
        for o in bpy.context.selected_objects:
            o.select_set(False)
        
    
    # reselect original objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selected:
        obj.select_set(True)

export()