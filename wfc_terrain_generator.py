import bpy
import time
import random
import numpy as np
from bpy.props import IntProperty, FloatProperty

print("===== WFC TERRAIN GENERATOR =====")
print("Starting script execution...")

try:
    # Clear existing objects
    print("Clearing existing objects...")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(confirm=False)
    print("Objects cleared successfully")
except Exception as e:
    print(f"Error clearing objects: {e}")

# Terrain module definitions
TERRAIN_TYPES = [
    "mountain_peak",
    "slope",
    "plateau",
    "valley_floor",
    "riverbed",
    "shoreline"
]

# Connection rules define which terrain types can be adjacent
CONNECTION_RULES = {
    "mountain_peak": ["mountain_peak", "slope"],
    "slope": ["mountain_peak", "slope", "plateau", "valley_floor"],
    "plateau": ["slope", "plateau", "valley_floor"],
    "valley_floor": ["slope", "plateau", "valley_floor", "riverbed"],
    "riverbed": ["valley_floor", "riverbed", "shoreline"],
    "shoreline": ["riverbed", "shoreline"]
}

# Height relationships for terrain types (relative height values)
HEIGHT_VALUES = {
    "mountain_peak": 3.0,
    "slope": 2.0,
    "plateau": 1.5,
    "valley_floor": 1.0,
    "riverbed": 0.5,
    "shoreline": 0.2
}

# Environmental objects that can be placed on terrain
OBJECT_TYPES = {
    "house": {
        "valid_terrain": ["plateau", "valley_floor"],
        "min_slope": 0,
        "max_slope": 0.2,
        "size": 0.5
    },
    "tree": {
        "valid_terrain": ["slope", "plateau", "valley_floor"],
        "min_slope": 0,
        "max_slope": 0.6,
        "size": 0.3
    },
    "rock": {
        "valid_terrain": ["mountain_peak", "slope", "plateau", "valley_floor", "shoreline"],
        "min_slope": 0,
        "max_slope": 0.8,
        "size": 0.2
    }
}


# Force Blender to update the viewport
def update_viewport():
    # This tells Blender to redraw all windows
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    
    # Give Blender time to process the redraw
    time.sleep(0.01)


# Wave Function Collapse implementation
class WaveFunctionCollapse:
    def __init__(self, grid_size=10, cell_size=2.0):
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.terrain_templates = {}
        self.env_templates = {}
        self.grid = np.zeros((grid_size, grid_size), dtype=object)
        self.terrain_collection = None
        self.placed_objects = []
        self.materials = {}
        
        # Initialize all cells with all possibilities
        for x in range(grid_size):
            for y in range(grid_size):
                self.grid[x, y] = TERRAIN_TYPES.copy()
        
        # Create terrain module templates
        for terrain_type in TERRAIN_TYPES:
            self.terrain_templates[terrain_type] = self.create_terrain_template(terrain_type)
            
        # Create environmental object templates
        for obj_type in OBJECT_TYPES.keys():
            self.env_templates[obj_type] = self.create_object_template(obj_type)

        # Create a collection for our generated terrain
        self.terrain_collection = bpy.data.collections.new("Generated_Terrain")
        bpy.context.scene.collection.children.link(self.terrain_collection)
                
    def get_neighbors(self, x, y):
        # Get the coordinates of neighboring cells
        neighbors = []
        if x > 0:
            neighbors.append((x-1, y))  # Left
        if x < self.grid_size - 1:
            neighbors.append((x+1, y))  # Right
        if y > 0:
            neighbors.append((x, y-1))  # Down
        if y < self.grid_size - 1:
            neighbors.append((x, y+1))  # Up
        return neighbors
    
    def collapse_cell(self, x, y, terrain_type=None):
        # Collapse a cell to a single state
        if terrain_type is None:
            # If no specific type is provided, randomly select from possibilities
            if isinstance(self.grid[x, y], list) and len(self.grid[x, y]) > 0:
                terrain_type = random.choice(self.grid[x, y])
            else:
                # Already collapsed or no possibilities
                return False
                
        # Collapse to the specified terrain type
        self.grid[x, y] = terrain_type
        
        # Create the terrain object immediately after collapsing
        self.create_terrain_module(x, y, terrain_type)
        
        # Propagate constraints to neighbors
        self.propagate_constraints(x, y)
        return True

    
    def create_terrain_module(self, x, y, terrain_type):
        """Create a physical terrain module at the specified grid position"""
        if not self.terrain_templates or terrain_type not in self.terrain_templates:
            print(f"Error: Template for {terrain_type} not found")
            return
            
        template = self.terrain_templates[terrain_type]
        
        # The new object is now the active object
        terrain_obj = template.copy()
        self.terrain_collection.objects.link(terrain_obj)

        # Give it a unique name
        terrain_obj.name = f"Terrain_{x}_{y}_{terrain_type}"
        
        # Make it visible
        terrain_obj.hide_viewport = False
        terrain_obj.hide_render = False
        
        # Position it
        terrain_obj.location = (x * self.cell_size, y * self.cell_size, 0)
        
        # Add to our list of placed objects
        self.placed_objects.append(terrain_obj)
        
    def propagate_constraints(self, x, y):
        # Apply constraints to neighboring cells based on the collapsed cell
        stack = [(x, y)]
        
        while stack:
            current_x, current_y = stack.pop()
            current_type = self.grid[current_x, current_y]
            
            # Skip if not collapsed yet
            if isinstance(current_type, list):
                continue
                
            # Get valid neighbors for this terrain type
            valid_neighbors = CONNECTION_RULES[current_type]
            
            # Update all neighboring cells
            for nx, ny in self.get_neighbors(current_x, current_y):
                neighbor_cell = self.grid[nx, ny]
                
                # Skip already collapsed cells
                if not isinstance(neighbor_cell, list):
                    continue
                    
                # Intersect with valid neighbors
                new_possibilities = [t for t in neighbor_cell if t in valid_neighbors]
                
                # If possibilities changed, update and add to stack
                if len(new_possibilities) < len(neighbor_cell):
                    self.grid[nx, ny] = new_possibilities
                    stack.append((nx, ny))
    
    def find_min_entropy_cell(self):
        # Find uncollapsed cell with fewest possibilities
        min_entropy = float('inf')
        min_cells = []
        
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                cell = self.grid[x, y]
                if isinstance(cell, list) and len(cell) > 0:
                    entropy = len(cell)
                    if entropy < min_entropy:
                        min_entropy = entropy
                        min_cells = [(x, y)]
                    elif entropy == min_entropy:
                        min_cells.append((x, y))
        
        if not min_cells:
            return None  # All cells collapsed
            
        # Randomly choose among minimum entropy cells
        return random.choice(min_cells)
    
    def run(self):
        """Run the WFC algorithm with integrated terrain generation"""
        print("Starting Wave Function Collapse algorithm with integrated terrain generation")
        
        # Seed with some initial terrain (e.g., mountain in center)
        center_x, center_y = self.grid_size // 2, self.grid_size // 2
        self.collapse_cell(center_x, center_y, "mountain_peak")
        
        # Track progress
        placed_cells = 1
        total_cells = self.grid_size * self.grid_size
        print(f"Terrain generation progress: {(placed_cells / total_cells) * 100:.1f}%")
        
        # Main WFC loop
        while True:
            # Find cell with minimum entropy
            min_cell = self.find_min_entropy_cell()
            
            # If all cells collapsed, we're done
            if min_cell is None:
                break
                
            # Collapse the chosen cell
            x, y = min_cell
            self.collapse_cell(x, y)
            placed_cells += 1
            
            # Update progress periodically
            if placed_cells % 5 == 0 or placed_cells == total_cells:
                progress = (placed_cells / total_cells) * 100
                print(f"Terrain generation progress: {progress:.1f}%")
                update_viewport()  # Refresh the viewport periodically
        
        self.place_environmental_objects()

        print("Terrain generation completed")
    
    def place_environmental_objects(self):
        """Place environmental objects on the terrain"""
        print("Placing environmental objects...")
        env_objects_data = []
        
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                terrain_type = self.grid[x, y]
                
                # Calculate approximate slope based on neighbors
                neighbors = self.get_neighbors(x, y)
                height_diffs = []
                for nx, ny in neighbors:
                    if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                        n_terrain = self.grid[nx, ny]
                        height_diffs.append(abs(HEIGHT_VALUES[terrain_type] - HEIGHT_VALUES[n_terrain]))
                
                slope = max(height_diffs) if height_diffs else 0
                
                # Try to place objects based on terrain type and slope
                for obj_type, obj_props in OBJECT_TYPES.items():
                    if (terrain_type in obj_props["valid_terrain"] and 
                        obj_props["min_slope"] <= slope <= obj_props["max_slope"]):
                        
                        # Random chance to place object
                        if random.random() < 0.3:  # 30% chance
                            # Random position within the cell
                            offset_x = random.uniform(-0.4, 0.4)
                            offset_y = random.uniform(-0.4, 0.4)
                            
                            self.create_env_object(
                                obj_type, 
                                x + offset_x, 
                                y + offset_y, 
                                terrain_type
                            )
                            
                            env_objects_data.append({
                                "type": obj_type,
                                "x": x + offset_x,
                                "y": y + offset_y,
                                "terrain": terrain_type
                            })
        
        return env_objects_data

    def create_env_object(self, obj_type, x, y, terrain_type):
        """Create an environmental object at the specified position"""
        if obj_type not in self.env_templates:
            print(f"Error: Template for {obj_type} not found")
            return
            
        template = self.env_templates[obj_type]
        
        # The new object is now the active object
        env_obj = template.copy()
        # Move it to our collection
        self.terrain_collection.objects.link(env_obj)
        
        # Give it a unique name
        env_obj.name = f"Env_{obj_type}_{x}_{y}"
        
        # Make it visible
        env_obj.hide_viewport = False
        env_obj.hide_render = False
        
        # Position on top of terrain
        terrain_height = HEIGHT_VALUES[terrain_type]
        env_obj.location = (
            x * self.cell_size, 
            y * self.cell_size, 
            terrain_height * 0.5  # Place on top of terrain
        )

        # Add to our list of placed objects
        self.placed_objects.append(env_obj)


    """
    TODO WILL REPLACE THESE WITH ACTUAL MESH
    """
    # Create placeholder modules (simple cubes with different colors)
    def create_terrain_template(self, terrain_type, size=1.0):
        print(f"Creating terrain module: {terrain_type}")
        try:
            # Create a cube
            bpy.ops.mesh.primitive_cube_add(size=size)
            module = bpy.context.active_object
            module.name = f"Module_{terrain_type}"
            print(f"Successfully created module: {module.name}")
        except Exception as e:
            print(f"Error creating terrain module {terrain_type}: {e}")
            return None
        
        # Assign different colors based on terrain type
        if terrain_type in self.materials:
            mat = self.materials[terrain_type]
        else:
            mat = bpy.data.materials.new(name=f"Material_{terrain_type}")
            mat.use_nodes = True
            
            # Set color based on terrain type
            if terrain_type == "mountain_peak":
                color = (0.8, 0.8, 0.8, 1)  # Light grey
                module.scale.z = HEIGHT_VALUES[terrain_type]
            elif terrain_type == "slope":
                color = (0.5, 0.4, 0.3, 1)  # Brown
                module.scale.z = HEIGHT_VALUES[terrain_type]
            elif terrain_type == "plateau":
                color = (0.3, 0.5, 0.3, 1)  # Green
                module.scale.z = HEIGHT_VALUES[terrain_type]
            elif terrain_type == "valley_floor":
                color = (0.2, 0.6, 0.2, 1)  # Darker green
                module.scale.z = HEIGHT_VALUES[terrain_type]
            elif terrain_type == "riverbed":
                color = (0.1, 0.3, 0.8, 1)  # Blue
                module.scale.z = HEIGHT_VALUES[terrain_type]
            elif terrain_type == "shoreline":
                color = (0.8, 0.7, 0.5, 1)  # Sand color
                module.scale.z = HEIGHT_VALUES[terrain_type]
            
            mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = color
        
        if module.data.materials:
            module.data.materials[0] = mat
        else:
            module.data.materials.append(mat)
            
        return module

    def create_object_template(self, obj_type):
        # Create environmental objects
        if obj_type == "house":
            bpy.ops.mesh.primitive_cube_add(size=OBJECT_TYPES[obj_type]["size"])
            obj = bpy.context.active_object
            obj.scale.z = 0.8  # Adjust height
        elif obj_type == "tree":
            # Simple tree - cube base with cone top
            bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.4)
            trunk = bpy.context.active_object
            trunk.location.z = 0.2
            
            bpy.ops.mesh.primitive_cone_add(radius1=0.3, depth=0.6)
            leaves = bpy.context.active_object
            leaves.location.z = 0.6
            
            # Join the objects
            bpy.ops.object.select_all(action='DESELECT')
            trunk.select_set(True)
            leaves.select_set(True)
            bpy.context.view_layer.objects.active = trunk
            bpy.ops.object.join()
            
            obj = trunk
        elif obj_type == "rock":
            bpy.ops.mesh.primitive_ico_sphere_add(radius=OBJECT_TYPES[obj_type]["size"])
            obj = bpy.context.active_object
            
        obj.name = f"Env_{obj_type}"
        
        # Create and assign material
        mat = bpy.data.materials.new(name=f"Material_{obj_type}")
        mat.use_nodes = True
        
        if obj_type == "house":
            color = (0.8, 0.2, 0.2, 1)  # Red
        elif obj_type == "tree":
            color = (0.0, 0.4, 0.0, 1)  # Dark green
        elif obj_type == "rock":
            color = (0.5, 0.5, 0.5, 1)  # Grey
            
        mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = color
        
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
            
        # Hide the object from view (it will be used as a template)
        obj.hide_viewport = True
        obj.hide_render = True
        
        return obj

# UI Panel class
class WFC_PT_TerrainGenerator(bpy.types.Panel):
    bl_label = "WFC Terrain Generator"
    bl_idname = "WFC_PT_TerrainGenerator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    
    def draw(self, context):
        layout = self.layout
        
        col = layout.column()
        col.prop(context.scene, "wfc_grid_size", text="Grid Size")
        col.prop(context.scene, "wfc_cell_size", text="Cell Size")
        
        col.separator()
        
        row = layout.row()
        row.scale_y = 2.0
        row.operator("wfc.run", text="Generate Terrain")

# Operator for generating terrain
class WFC_OT_GenerateTerrain(bpy.types.Operator):
    bl_idname = "wfc.run"
    bl_label = "Generate Terrain"
    bl_description = "Generate procedural terrain using Wave Function Collapse algorithm"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        grid_size = context.scene.wfc_grid_size
        cell_size = context.scene.wfc_cell_size
        
        wfc = WaveFunctionCollapse(grid_size=grid_size, cell_size=cell_size)
        result = wfc.run()
        self.report({'INFO'}, result)
        
        return {'FINISHED'}

# Register properties
def register_properties():
    bpy.types.Scene.wfc_grid_size = IntProperty(
        name="Grid Size",
        description="Size of the terrain grid",
        default=10,
        min=3,
        max=50
    )
    
    bpy.types.Scene.wfc_cell_size = FloatProperty(
        name="Cell Size",
        description="Size of each terrain cell",
        default=2.0,
        min=0.5,
        max=10.0
    )

# Registration functions
def register():
    bpy.utils.register_class(WFC_PT_TerrainGenerator)
    bpy.utils.register_class(WFC_OT_GenerateTerrain)
    register_properties()

def unregister():
    bpy.utils.unregister_class(WFC_PT_TerrainGenerator)
    bpy.utils.unregister_class(WFC_OT_GenerateTerrain)
    del bpy.types.Scene.wfc_grid_size
    del bpy.types.Scene.wfc_cell_size

# Execute standalone without registering as addon
print("Attempting to execute as standalone script...")
# Run directly instead of registering as addon
register_properties()
print("Properties registered successfully")

# Execute terrain generation with default parameters
print("Generating terrain with default parameters...")
# Run WFC algorithm
print("Running Wave Function Collapse algorithm...")
wfc = WaveFunctionCollapse(grid_size=10)
wfc.run()
print("WFC algorithm completed successfully")



# Uncomment to register as addon:
# try:
#     register()
#     print("WFC Terrain Generator addon registered. Find the tool in the N-panel under 'Tool' category.")
# except Exception as e:
#     print(f"Error registering addon: {e}")
#     import traceback
#     traceback.print_exc()

