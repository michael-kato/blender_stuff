
import os
import copy
import bpy


export_path = r"C:\Users\rawmeat\Documents\Unreal Projects\gunship\Content\Model"

def export():
    
    # TODO: just put in object 
    bpy.ops.object.editmode_toggle()
    
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
        
        file_path = os.path.join(export_path, f"{obj.name}.gltf")
        
        # in try/except because we always want the object back in it's location even if things fail
        try:
            bpy.ops.export_scene.gltf(filepath=file_path, use_selection=True, export_format="GLTF_SEPARATE", 
                export_hierarchy_flatten_objs=True, will_save_settings=True)
            #export_hierarchy_flatten_objs 
            #export_apply 
            #export_hierarchy_full_collections 
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