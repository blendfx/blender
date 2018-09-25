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


def set_mask_mode(context, mask):
    # Set mask mode in Image and Clip Editor
    scn = context.scene
    active_node = scn.node_tree.nodes.active
    # set mode to mask and select the mask
    for area in context.screen.areas:
        active_space = area.spaces.active
        if area.type == 'IMAGE_EDITOR' or area.type == 'CLIP_EDITOR':
            active_space.mode = 'MASK'
            active_space.mask = mask
        # if it is the image editor, assign the viewer node if possible
        elif area.type == 'IMAGE_EDITOR':
            try:
                active_space.image = bpy.data.images["Viewer Node"]
            except:
                print("There is no Viewer Node yet")


def selected_mask_points(context):
    mask = context.space_data.mask
    pointlist = []
    try:
        for l in mask.layers: 
            if not l.hide and not l.hide_select:
                for s in l.splines:
                    for p in s.points:
                        if p.select:
                            pointlist.append(p)
        return pointlist
    except:
        print("no points selected?")


class MASK_OT_activate_mask(Operator):
    """Make the active mask node the active mask in Clip/Image Editor"""
    bl_idname = "mask.activate_mask"
    bl_label = "Activate Mask"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'NODE_EDITOR' and space.tree_type == 'CompositorNodeTree'

    def execute(self, context):
        scn = context.scene
        active_node = scn.node_tree.nodes.active

        if active_node.type == 'MASK':
            the_mask = active_node.mask
            print(the_mask)
            set_mask_mode(context, the_mask)
        return {'FINISHED'}


class MASK_OT_new_mask_layer(Operator):
    """Create a new masklayer, only edit this one"""
    bl_idname = "mask.new_mask"
    bl_label = "New Masklayer"

    def execute(self, context):
        mask = context.space_data.mask
        for l in mask.layers:
            l.hide_select = True
        bpy.ops.mask.layer_new()      
        return {'FINISHED'}
        

class MASK_OT_enable_self_intersection_check(Operator):
    """Enable Self Intersection Check of active spline"""
    bl_idname = "mask.enable_self_intersection_check"
    bl_label = "Enable Self-Intersection Check"

    def execute(self, context):
        mask = context.space_data.mask
        for s in mask.layers.active.splines:
            s.use_self_intersection_check = True
        return {'FINISHED'}


class MASK_OT_set_to_add(Operator):
    """Set the current layer to Add"""
    bl_idname = "mask.set_add"
    bl_label = "Set Add"

    def execute(self, context):
        mask = context.space_data.mask
        active_layer = mask.layers.active
        active_layer.blend="MERGE_ADD"
        return {'FINISHED'}


class MASK_OT_set_to_subtract(Operator):
    """Set current layer to Subtract"""
    bl_idname = "mask.set_subtract"
    bl_label = "Set Subtract"

    def execute(self, context):
        mask = context.space_data.mask
        active_layer = mask.layers.active
        active_layer.blend = "MERGE_SUBTRACT"
        return {'FINISHED'}


class MASK_OT_toggle_drawtype(Operator):
    """Set the drawtype to smooth and toggle between white and outline"""
    bl_idname = "mask.toggle_drawtype"
    bl_label = "Toggle Drawtype"

    def execute(self, context):
        sc = context.space_data
        sc.show_mask_smooth = True
        if sc.mask_draw_type == "OUTLINE":
            sc.mask_draw_type = "WHITE"
        else:
            sc.mask_draw_type = "OUTLINE"
        return {'FINISHED'}
        

class MASK_OT_set_marker_drawtype(Operator):
    """Don't draw markers"""
    bl_idname = "mask.set_marker_drawtype"
    bl_label = "Set Marker Drawtype"

    def execute(self, context):
        sc = context.space_data
        sc.show_marker_pattern = False
        sc.show_marker_search= False
        sc.show_track_path = False
        return {'FINISHED'}
        

class MASK_OT_clear_keyframes(Operator):
    """Clear all keyframes of current mask"""
    bl_idname = "mask.clear_keyframes"
    bl_label = "Clear keyframes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        current_frame = scn.frame_current
        # we wanna make sure that we stay on the current state of the mask (frame)
        for f in range(scn.frame_current+1, scn.frame_end+1):
            scn.frame_set(f)
            bpy.ops.mask.shape_key_clear()
        for f in range(scn.frame_start, scn.frame_current-2):
            scn.frame_set(f)
            bpy.ops.mask.shape_key_clear()
        scn.frame_current = current_frame
        return {'FINISHED'}
        

class MASK_OT_isolate_layer(Operator):
    """Isolate the currently selected layer"""
    bl_idname = "mask.isolate_layer"
    bl_label = "Isolate Mask Layer"

    def execute(self, context):
        mask = context.space_data.mask
        active_layer = mask.layers.active
        for ml in mask.layers:
            ml.hide_select = True
        active_layer.hide_select = False
        return {'FINISHED'}


class MASK_OT_switch_editor(bpy.types.Operator):
    """Toggle between Image and Clip Editor, while keeping same mode and display aspect"""
    bl_idname = "mask.switch_editor"
    bl_label = "Switch Editor"

    def execute(self, context):
        scn = context.scene
        for area in context.screen.areas: 
            active_space = area.spaces.active
            if area.type == "CLIP_EDITOR":
                if scn.node_tree and scn.node_tree.nodes.get("Viewer"):
                    mask = active_space.mask
                    area.type = "IMAGE_EDITOR"
                    active_area = area.spaces.active
                    # this only works if a Viewer Node exists
                    if bpy.data.images["Viewer Node"]:
                        active_area.image = bpy.data.images["Viewer Node"]
                        active_area.image.display_aspect[0] = scn.active_clip.tracking.camera.pixel_aspect
                    active_area.mode = "MASK"
                    active_area.mask = mask
                else:
                    self.report({"INFO"}, "You need a Viewer Node for this to work")

            elif area.type == "IMAGE_EDITOR":
                mask = active_space.mask
                area.type = "CLIP_EDITOR"
                active_area = area.spaces.active
                active_area.mode = "MASK"
                active_area.mask = mask

        return {'FINISHED'}


class MASK_OT_parent_marker_visibility(Operator):
    """Toggle visibility of parent markers of selected points"""
    bl_idname = "mask.parent_marker_visibility"
    bl_label = "Parent Marker Visibilty"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        markers = set() # Using a set helps to avoid double entries
        for p in selected_mask_points(context):
            if p.parent.sub_parent:
                markers.add(p.parent.sub_parent)
        for m in markers:
            track = context.space_data.clip.tracking.objects.active.tracks[m]
            if track.hide == True:
                track.hide = False
            else:
                track.hide = True
        return {'FINISHED'}


class MASK_OT_toggle_marker_visibility(Operator):
    """Toggle visibility of all markers of current clip"""
    bl_idname = "mask.toggle_marker_visibility"
    bl_label = "Toggle Marker Visibility"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'CLIP_EDITOR'

    def execute(self, context):
        hidden = False
        tracks = context.space_data.clip.tracking.objects.active.tracks
        for t in tracks:
            if t.hide == True:
                hidden = True
        if hidden:
            for t in tracks:
                t.hide = False
        else:
            for t in tracks:
                t.hide = True
        return {'FINISHED'}


class MASK_PIE_mask_editing(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Masking Pie"
    bl_idname = "mask.mask_editing_pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        pie.operator("mask.clear_keyframes", icon='SPACE3')
        pie.operator("mask.switch_direction", icon="ARROW_LEFTRIGHT")
        pie.operator("mask.cyclic_toggle", icon="CURVE_BEZCIRCLE")
        pie.operator("mask.handle_type_set", icon='IPO_BEZIER')
        pie.operator("mask.feather_weight_clear", icon='X')
        pie.operator("transform.transform", text="Scale Feather", icon="MAN_SCALE").mode = 'MASK_SHRINKFATTEN'
        pie.operator("mask.shape_key_feather_reset", icon='ANIM')
        pie.operator("mask.enable_self_intersection_check")
        # pie.prop(context.scene.tool_settings, "use_keyframe_insert_auto",text="Enable Autokey")


class MASK_PIE_mask_layers(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Masking Pie"
    bl_idname = "mask.mask_layer_pie"

    def draw(self, context):
        active_layer  = context.space_data.mask.layers.active
        layout = self.layout
        pie = layout.menu_pie()

        pie.operator("mask.new_mask", icon='MESH_PLANE') 
        pie.operator("mask.switch_editor", icon='IMAGE_COL')
        pie.operator("mask.isolate_layer", icon='RESTRICT_SELECT_OFF')
        pie.prop(active_layer, "invert", text="Invert Layer", icon='IMAGE_ALPHA')
        pie.operator("mask.set_subtract", icon='ZOOMOUT')
        pie.operator("mask.set_add", icon='ZOOMIN')
        pie.operator("mask.select_linked", icon="LINKED")
        #pie.operator("mask.lock_inactive_layers", icon='CONSTRAINT') 


class MASK_PIE_mask_display(Menu):
    bl_idname = "mask.mask_display_pie"
    bl_label = "Mask Display Options"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        pie.operator("mask.toggle_marker_visibility", icon="VISIBLE_IPO_ON")
        pie.operator("mask.parent_marker_visibility", icon="GHOST_ENABLED")
        pie.operator("mask.toggle_drawtype", icon='CONSTRAINT') 
        pie.prop(context.space_data, "show_mask_overlay", text="Show Mask Overlay", icon ="IMAGE_ZDEPTH")

       
        

########## register ############
classes = (
    MASK_PIE_mask_editing,
    MASK_PIE_mask_layers,
    MASK_PIE_mask_display,
    MASK_OT_new_mask_layer,
    MASK_OT_set_to_subtract,
    MASK_OT_set_to_add,
    MASK_OT_toggle_drawtype,
    MASK_OT_set_marker_drawtype,
    MASK_OT_isolate_layer,
    MASK_OT_clear_keyframes,
    MASK_OT_switch_editor,
    MASK_OT_parent_marker_visibility,
    MASK_OT_toggle_marker_visibility,
    MASK_OT_enable_self_intersection_check,
    MASK_OT_activate_mask
    )

def register():
    for c in classes:
        bpy.utils.register_class(c)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Mask Editing')
    
    kmi = km.keymap_items.new('wm.call_menu_pie', 'E', 'PRESS').properties.name = "mask.mask_editing_pie"
    kmi = km.keymap_items.new('wm.call_menu_pie', 'Q', 'PRESS').properties.name = "mask.mask_layer_pie"
    kmi = km.keymap_items.new('wm.call_menu_pie', 'W', 'PRESS').properties.name = "mask.mask_display_pie"

    km = wm.keyconfigs.addon.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
    kmi = km.keymap_items.new('mask.activate_mask', 'ACTIONMOUSE', 'DOUBLE_CLICK')



def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
