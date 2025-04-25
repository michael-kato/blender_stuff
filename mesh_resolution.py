import bpy
import bmesh
import mathutils
import math
import time
import random
from bpy.props import FloatProperty, IntProperty, BoolProperty, EnumProperty


# Force Blender to update the viewport
def update_viewport():
    # This tells Blender to redraw all windows
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    
    # Give Blender time to process the redraw
    time.sleep(0.01)

class MESH_OT_AdjustResolution(bpy.types.Operator):
    """Adjust mesh resolution based on target triangle size"""
    bl_idname = "mesh.adjust_resolution"
    bl_label = "Adjust Mesh Resolution"
    bl_options = {'REGISTER', 'UNDO'}
    
    target_tri_size: FloatProperty(
        name="Target Triangle Size",
        description="Target size of triangle in Blender units",
        default=0.25,
        min=0.01,
        max=10.0,
        unit='LENGTH'
    )
    
    prepare_for_baking: BoolProperty(
        name="Optimize for Baking",
        description="Prepare mesh for vertex lighting baking",
        default=True
    )

    def execute(self, context):
        obj = context.active_object
        
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}
        
        # Store original mode and switch to object mode
        original_mode = context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Get method from scene settings
        self.target_tri_size = context.scene.mesh_res_target_size
        self.prepare_for_baking = context.scene.mesh_res_optimize_baking
        
        # Start timing for performance measurement
        start_time = time.time()
        
        self.report({'INFO'}, f"Applying subdivision...")
        
        # Update viewport to show progress message
        bpy.context.view_layer.update()
        
        # Apply subdivision
        self.apply_subdivision(obj)
        
        # Optimize the mesh if needed
        if self.prepare_for_baking:
            self.optimize_for_baking(obj)
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Restore original mode
        bpy.ops.object.mode_set(mode=original_mode)
        
        # Final report with timing info
        self.report({'INFO'}, f"Adjusted mesh resolution. " +
                              f"Target size: {self.target_tri_size} units. " +
                              f"Processed in {elapsed_time:.2f} seconds.")
        return {'FINISHED'}
    
    def apply_subdivision(self, obj):
        """Apply subdivision based on selected method"""
        # Use BMesh for more control
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        self.delaunay_adaptive_tessellation(bm, self.target_tri_size)
            
        # Update the mesh
        bm.to_mesh(obj.data)
        bm.free()
        
        # Update mesh
        obj.data.update()
    
    def delaunay_adaptive_tessellation(self, bm, target_face_area, max_iterations=10, preserve_boundaries=True):
        """
        Performs adaptive tessellation on an existing mesh using Delaunay criteria.
        
        This function preserves the original mesh topology and attributes (UVs, normals, etc.)
        while ensuring convex triangulation. It works by first triangulating all non-triangular
        faces using Delaunay criteria, then subdividing edges until the target face area is reached.
        
        Args:
            bm (bmesh.types.BMesh): The BMesh to tessellate
            target_face_area (float): Target maximum face area in square blender units
            max_iterations (int): Maximum subdivision iterations to prevent infinite loops
            preserve_boundaries (bool): Whether to preserve boundary edges
            
        Returns:
            None
        """
        
        # Ensure lookup tables are fresh
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        
        # Use Delaunay triangulation via BMesh operator
        bmesh.ops.triangulate(bm, quad_method='BEAUTY', ngon_method='BEAUTY')
        
        # Update our lookup tables after topology changes
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        
        # Step 2: Iterative subdivision until target face area is achieved
        for _ in range(max_iterations):
            # Identify large faces that need subdivision
            large_faces = [f for f in bm.faces if f.calc_area() > target_face_area]
            divided_faces = set()
            
            # If no large faces remain, we're done
            if not large_faces:
                break
                
            # Identify edges to subdivide
            edges_to_subdivide = []
            seen_edges = set()  # Track edges we've already marked for subdivision
            
            for face in large_faces:
                # For each large face, find its longest edge
                longest_edge = None
                max_length = 0
                
                for edge in face.edges:
                    # Skip boundary edges if specified
                    if preserve_boundaries and edge.is_boundary:
                        continue
                        
                    # Skip edges we've already decided to subdivide, but save the face
                    if edge.index in seen_edges:
                        divided_faces.add(face)
                        continue
                        
                    length = edge.calc_length()
                    if length > max_length:
                        max_length = length
                        longest_edge = edge
                
                # Add the longest edge to our subdivision list
                if longest_edge and longest_edge.index not in seen_edges:
                    edges_to_subdivide.append(longest_edge)
                    seen_edges.add(longest_edge.index)
                    divided_faces.add(face)
            
            # If no edges to subdivide (could happen if all are boundaries), break
            if not edges_to_subdivide:
                break
                
            # Subdivide the selected edges (one cut per edge)
            bmesh.ops.subdivide_edges(bm, edges=edges_to_subdivide, cuts=1, use_single_edge =True)
            bmesh.ops.triangulate(bm, faces=list(divided_faces), quad_method='BEAUTY', ngon_method='BEAUTY')

            # Update our topology after modifications
            bm.faces.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.verts.ensure_lookup_table()

    
    def optimize_for_baking(self, obj):
        """Prepare mesh for vertex lighting/baking"""
        # Add custom data layers for vertex lighting if they don't exist
        mesh = obj.data
        
        # Add vertex colors if needed for baking
        if not mesh.vertex_colors:
            mesh.vertex_colors.new(name="BakedLighting")
        
        # Add UVs if needed for baking
        if not mesh.uv_layers:
            mesh.uv_layers.new(name="LightmapUVs")
            
            # We could unwrap here if needed
            # bpy.ops.object.mode_set(mode='EDIT')
            # bpy.ops.mesh.select_all(action='SELECT')
            # bpy.ops.uv.smart_project()
            # bpy.ops.object.mode_set(mode='OBJECT')


class VIEW3D_PT_MeshResolutionPanel(bpy.types.Panel):
    """Panel for Mesh Resolution Tool"""
    bl_label = "Mesh Resolution Tool"
    bl_idname = "VIEW3D_PT_mesh_resolution"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    
    def draw(self, context):
        layout = self.layout
        
        col = layout.column(align=True)
        col.operator("mesh.adjust_resolution")
        
        # Tool settings
        box = layout.box()
        box.label(text="Resolution Settings")
        
        col = box.column(align=True)
        col.prop(context.scene, "mesh_res_target_size", text="Target Size")
        
        row = box.row()
        row.prop(context.scene, "mesh_res_optimize_baking")
            
        # Analysis button
        layout.operator("mesh.analyze_resolution")
        
        # Show analysis results if available
        if hasattr(context.scene, "mesh_analysis_tri_count") and context.scene.mesh_analysis_tri_count > 0:
            box = layout.box()
            box.label(text="Mesh Analysis")
            
            col = box.column(align=True)
            col.label(text=f"Triangles: {context.scene.mesh_analysis_tri_count}")
            col.label(text=f"Avg Size: {context.scene.mesh_analysis_avg_size:.3f}")
            col.label(text=f"Size Range: {context.scene.mesh_analysis_min_size:.3f} - {context.scene.mesh_analysis_max_size:.3f}")


def add_mesh_resolution_props():
    """Add properties to the scene"""
    bpy.types.Scene.mesh_res_target_size = FloatProperty(
        name="Target Triangle Size",
        description="Target size of triangles in Blender units",
        default=0.25,
        min=0.01,
        max=10.0,
        unit='LENGTH'
    )
    
    bpy.types.Scene.mesh_res_optimize_baking = BoolProperty(
        name="Optimize for Baking",
        description="Prepare mesh for vertex lighting baking",
        default=True
    )
    
def remove_mesh_resolution_props():
    """Remove custom properties"""
    del bpy.types.Scene.mesh_res_target_size
    del bpy.types.Scene.mesh_res_optimize_baking


# Calculate actual mesh metrics for analysis
def analyze_mesh(obj, bm):
    """Analyze mesh metrics for informational purposes"""
    stats = {
        'tri_count': 0,
        'avg_tri_size': 0,
        'total_area': 0
    }

    mesh = obj.data
    
    # Calculate mesh statistics
    total_area = 0
    tris = mesh.loop_triangles
    tri_count = len(tris)
    
    for tri in tris:
        total_area += tri.area
    
    # Calculate statistics
    stats['tri_count'] = tri_count
    stats['avg_tri_size'] = total_area / tri_count
    stats['total_area'] = total_area
    
    return stats 


class MESH_OT_AnalyzeMesh(bpy.types.Operator):
    """Analyze mesh metrics for resolution information"""
    bl_idname = "mesh.analyze_resolution"
    bl_label = "Analyze Mesh Resolution"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        obj = context.active_object
        dg = context.evaluated_depsgraph_get()
        
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}
        
        # Analyze the mesh
        bm = bmesh.new()
        bm.from_object(obj, dg)
        metrics = analyze_mesh(obj, bm)
        
        # Display results
        self.report({'INFO'}, f"Mesh Analysis: {metrics['tri_count']} trigons, " 
                              f"Avg size: {metrics['avg_tri_size']:.3f}")
        
        # Store in scene properties for UI display
        context.scene.mesh_analysis_tri_count = metrics['tri_count']
        context.scene.mesh_analysis_avg_size = metrics['avg_tri_size']
        
        return {'FINISHED'}


# Register mesh analysis properties
def add_mesh_analysis_props():
    bpy.types.Scene.mesh_analysis_tri_count = bpy.props.IntProperty(default=0)
    bpy.types.Scene.mesh_analysis_avg_size = bpy.props.FloatProperty(default=0.0)

def remove_mesh_analysis_props():
    del bpy.types.Scene.mesh_analysis_tri_count
    del bpy.types.Scene.mesh_analysis_avg_size


classes = (
    MESH_OT_AdjustResolution,
    MESH_OT_AnalyzeMesh,
    VIEW3D_PT_MeshResolutionPanel
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    add_mesh_resolution_props()
    add_mesh_analysis_props()

def unregister():
    remove_mesh_resolution_props()
    remove_mesh_analysis_props()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
