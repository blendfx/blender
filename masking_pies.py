bl_info = {
"name": "Masking Pies",
"author": "Sebastian Koenig",
"version": (1, 0),
"blender": (2, 7, 2),
"location": "Clip Editor > Masking Pies",
"description": "Pie Controls for Masking",
"warning": "",
"wiki_url": "",
"tracker_url": "",
"category": "Compositing"}



import bpy
from bpy.types import Menu, Operator

############### FUNCTIONS ##########################

def CLIP_spaces_walk(context, all_screens, tarea, tspace, callback, *args):
    screens = bpy.data.screens if all_screens else [context.screen]

    for screen in screens:
        for area in screen.areas:
            if area.type == tarea:
                for space in area.spaces:
                    if space.type == tspace:
                        callback(space, *args)


class MASK_setup_masking_scene(Operator):
    """docstring for MASK_setup_masking_scene"""
    bl_label = "Setup Masking Scene"
    bl_idname = "mask.setup_masking_scene"

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        if sc.type != 'CLIP_EDITOR' or sc.type != 'IMAGE_EDITOR':
            return False
        clip = sc.clip
        return clip 

    
    @staticmethod
    def _needSetupNodes(context):
        scene = context.scene
        tree = scene.node_tree
        if not tree:
            # No compositor node tree found, time to create it!
            return True
        for node in tree.nodes:
            if node.type in {'MOVIECLIP'}:
                return False
        return True
   
    @staticmethod
    def _wipeDefaultNodes(tree):
        if len(tree.nodes) != 2:
            return False
        types = [node.type for node in tree.nodes]
        types.sort()
        if types[0] == 'COMPOSITE' and types[1] == 'R_LAYERS':
            while tree.nodes:
                tree.nodes.remove(tree.nodes[0])

    def _setupNodes():
        if not self._needSetupNodes(context):
            # compositor nodes were already setup or even changes already
            # do nothing to prevent nodes damage
            return
        movie = tree.nodes.new(type='CompositorNodeMovieClip')
        movie.clip = clip

    # Enable backdrop for all compositor spaces
    def setup_space(space):
        space.show_backdrop = True
        CLIP_spaces_walk(context, True, 'NODE_EDITOR', 'NODE_EDITOR',
                     setup_space)
        scene = context.scene
        sc = context.space_data
        scene.use_nodes = True
        tree = scene.node_tree
        clip = sc.clip
        self._wipeDefaultNodes(tree)
        return {'FINISHED'}

    def execute(self, context):
        scene = context.scene
        current_active_layer = scene.active_layer
        self._setupScene(context)
        self._setupNodes(context)
        return {'FINISHED'}


class MASK_newmasklayer(Operator):
    """docstring for MASK_newmasklayer"""
    bl_idname = "mask.new_mask"
    bl_label = "New Masklayer"

    def execute(self, context):
        mask = context.space_data.mask
        active_layer = mask.layers.active
        if active_layer:
            active_layer.hide_select=True
        bpy.ops.mask.layer_new()      
        return {'FINISHED'}
        

class MASK_set_to_add(Operator):
    """docstring for MASK_newmasklayer"""
    bl_idname = "mask.set_add"
    bl_label = "Set Add"

    def execute(self, context):
        mask = context.space_data.mask
        active_layer = mask.layers.active
        active_layer.blend="MERGE_ADD"
        return {'FINISHED'}


class MASK_lock_inactive_layers(Operator):
    """docstring for MASK_newmasklayer"""
    bl_idname = "mask.lock_inactive_layers"
    bl_label = "Lock Inactive Layers"

    def execute(self, context):
        mask = context.space_data.mask
        active_layer = mask.layers.active
        for ml in mask.layers:
            ml.hide_select = True
        active_layer.hide_selecti = False
        return {'FINISHED'}

        
        
class MASK_set_drawtype(Operator):
    """docstring for MASK_newmasklayer"""
    bl_idname = "mask.set_drawtype"
    bl_label = "Set Drawtype"

    def execute(self, context):
        sc = context.space_data
        sc.show_mask_smooth = True
        sc.mask_draw_type = "WHITE"
        return {'FINISHED'}
        

class MASK_set_marker_drawtype(Operator):
    """docstring for MASK_newmasklayer"""
    bl_idname = "mask.set_marker_drawtype"
    bl_label = "Set Marker Drawtype"

    def execute(self, context):
        sc = context.space_data
        sc.show_marker_pattern = False
        sc.show_marker_search= False
        sc.show_track_path = False
        return {'FINISHED'}
        
      
class MASK_set_to_subtract(Operator):
    """docstring for MASK_newmasklayer"""
    bl_idname = "mask.set_subtract"
    bl_label = "Set Subtract"

    def execute(self, context):
        mask = context.space_data.mask
        active_layer = mask.layers.active
        active_layer.blend = "MERGE_SUBTRACT"
        return {'FINISHED'}
        

class MASK_clear_keyframes(Operator):
    """docstring for MASK_newmasklayer"""
    bl_idname = "mask.clear_keyframes"
    bl_label = "Clear keyframes"

    def execute(self, context):
        scene = context.scene
        current_frame = scene.frame_current
        bpy.ops.mask.shape_key_clear()
        # we wanna make sure that we stay on the current state of the mask (frame)
        for f in range(scene.frame_current, scene.frame_end):
            scene.frame_set(f)
            bpy.ops.mask.shape_key_clear()
        for f in range(scene.frame_start, scene.frame_current-1):
            scene.frame_set(f)
            bpy.ops.mask.shape_key_clear()
        scene.frame_current = current_frame
        return {'FINISHED'}
        

class CLIP_PIE_mask_editing(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Masking Pie"
    bl_idname = "clip.mask_editing_pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        pie.operator("mask.handle_type_set", icon='IPO_BEZIER')
        pie.operator("mask.cyclic_toggle", icon="CURVE_BEZCIRCLE")
        pie.operator("mask.select_linked", icon="LINKED")
        pie.operator("mask.switch_direction", icon="ARROW_LEFTRIGHT")
        pie.operator("mask.feather_weight_clear", icon='X')
        pie.operator("transform.transform", text="Scale Feather", icon="MAN_SCALE").mode = 'MASK_SHRINKFATTEN'
        pie.operator("mask.shape_key_feather_reset", icon='ANIM')
        pie.prop(bpy.context.scene.tool_settings, "use_keyframe_insert_auto",text="Enable Autokey")


class CLIP_PIE_masklayers(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Masking Pie"
    bl_idname = "clip.masklayer_pie"

    def draw(self, context):
        mask = context.space_data.mask
        active_layer = mask.layers.active

        layout = self.layout
        pie = layout.menu_pie()
        pie.operator("mask.primitive_square_add", icon='MESH_PLANE')
        pie.operator("mask.primitive_circle_add", icon='MESH_CIRCLE')
        pie.operator("mask.new_mask", icon='MESH_PLANE') 
        pie.prop(context.space_data, "show_mask_overlay", text="Show Mask Overlay", icon ="IMAGE_ZDEPTH")
        pie.operator("mask.set_subtract", icon='ZOOMOUT')
        pie.operator("mask.set_add", icon='ZOOMIN')
        pie.prop(active_layer, "invert", text="Invert Layer", icon='IMAGE_ALPHA')
        pie.operator("mask.set_drawtype", icon='CONSTRAINT') 
        #pie.operator("mask.lock_inactive_layers", icon='CONSTRAINT') 
        

########## register ############
classes = (
    CLIP_PIE_mask_editing,
    CLIP_PIE_masklayers,
    MASK_lock_inactive_layers,
    MASK_newmasklayer,
    MASK_set_to_subtract,
    MASK_set_to_add,
    MASK_setup_masking_scene,
    MASK_set_drawtype,
    MASK_set_marker_drawtype,
    MASK_clear_keyframes,
    )

def register():
    for c in classes:
        bpy.utils.register_class(c)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Mask Editing')
    
    kmi = km.keymap_items.new('wm.call_menu_pie', 'E', 'PRESS').properties.name = "clip.mask_editing_pie"
    kmi = km.keymap_items.new('wm.call_menu_pie', 'Q', 'PRESS').properties.name = "clip.masklayer_pie"



def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
