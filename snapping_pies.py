bl_info = {
    "name": "Snapping Pies",
    "author": "Sebastian Koenig, Ivan Santic",
    "version": (0, 3),
    "blender": (2, 8, 0),
    "description": "Custom Pie Menus",
    "category": "3D View",}



import bpy
from bpy.types import Menu, Operator, Panel


########### CUSTOM OPERATORS ###############


class VIEW3D_OT_toggle_pivot(Operator):
    """Toggle between 3D-Cursor and Median pivoting"""
    bl_idname = "scene.toggle_pivot"
    bl_label = "Toggle Pivot"
 
    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'VIEW_3D'
 
    def execute(self, context):
        pivot = context.space_data.pivot_point
        if pivot == "CURSOR":
            context.space_data.pivot_point = "MEDIAN_POINT"
        elif pivot == "INDIVIDUAL_ORIGINS":
            context.space_data.pivot_point = "MEDIAN_POINT"
        else:
            context.space_data.pivot_point = "CURSOR"
        return {'FINISHED'}
 


class VIEW3D_OT_object_to_marker(Operator):
    "Set the object's origin to the mesh selection and place the object to the active 3d Marker"
    bl_idname = "object.object_to_marker"
    bl_label = "Snap Origin to 3D Marker"

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        clip = context.scene.active_clip
        average_error = clip.tracking.objects.active.reconstruction.average_error
        active_object = context.view_layer.objects.active
        return (sc.type == 'VIEW_3D' and average_error > 0.0 and active_object != context.scene.camera)

    def execute(self, context):
        cursor_location = context.scene.cursor.location.copy()
        active_object = context.view_layer.objects.active
        active_camera = context.scene.camera
        # make sure only the camera is selected
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = active_camera
        active_camera.select_set(True)
        bpy.ops.view3d.snap_cursor_to_selected()
        marker_location = context.scene.cursor.location.copy()
        active_camera.select_set(False)

        context.view_layer.objects.active = active_object
        active_object.select_set(True)
        active_object.location = marker_location
        context.scene.cursor.location = cursor_location

        return {'FINISHED'}


class VIEW3D_OT_origin_to_marker(Operator):
    "Set the object's origin to the mesh selection and place the object to the active 3d Marker"
    bl_idname = "object.origin_to_marker"
    bl_label = "Snap Origin to 3D Marker"

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        clip = context.scene.active_clip
        average_error = clip.tracking.objects.active.reconstruction.average_error
        return (sc.type == 'VIEW_3D' and context.object.mode == 'EDIT' and average_error > 0.0)

    def execute(self, context):
        cursor_location = context.scene.cursor.location.copy()

        # set origin to selected vertex
        bpy.ops.view3d.snap_cursor_to_selected()
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

        # store the location of the 3d marker
        active_object = context.view_layer.objects.active
        active_camera = context.scene.camera
        # make sure only the camera is selected
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = active_camera
        active_camera.select_set(True)
        bpy.ops.view3d.snap_cursor_to_selected()
        marker_location = context.scene.cursor.location.copy()
        active_camera.select_set(False)

        context.view_layer.objects.active = active_object
        active_object.select_set(True)
        active_object.location = marker_location
        context.scene.cursor.location = cursor_location
        return {'FINISHED'}

class VIEW3D_OT_origin_to_selected(Operator):
    "Set the object's origin to the 3d cursor. Works only in edit mode"
    bl_idname = "object.origin_to_selected"
    bl_label = "Origin to Selection"

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        return (sc.type == 'VIEW_3D' and context.object.mode == 'EDIT')

    def execute(self, context):
        cursor_location = context.scene.cursor.location.copy()
        bpy.ops.view3d.snap_cursor_to_selected()
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        context.scene.cursor.location = cursor_location
        return {'FINISHED'}


class VIEW3D_OT_origin_to_geometry(Operator):
    bl_idname="object.origin_to_geometry"
    bl_label="Origin to Geometry"

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        return (sc.type == 'VIEW_3D' and context.object.mode == 'EDIT')

    def execute(self, context):
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
        bpy.ops.object.mode_set(mode="EDIT")
        return {'FINISHED'}





#Menu Snap Element
class VIEW3D_PIE_SnapElementMenu(Menu):
    bl_label = "Snap Element"

    def draw(self, context):
        settings = bpy.context.scene.tool_settings
        layout = self.layout
        pie = layout.menu_pie()
        pie.prop(settings, "snap_element", expand=True)


#Menu Snap Element
class VIEW3D_OT_SetPivotIndividual(Operator):
    bl_label = "Individual Origins"
    bl_idname = "object.setpivotindidual"

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        return (sc.type == 'VIEW_3D')

    def execute(self, context):
        bpy.context.space_data.pivot_point = "INDIVIDUAL_ORIGINS"
        return {'FINISHED'}
        






################### PIES #####################

class VIEW3D_PIE_MT_snapping_pie(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Snapping and Origin"
    bl_idname = "VIEW3D_PIE_MT_snapping_pie"

    def draw(self, context):
        context = bpy.context
        layout = self.layout
        tool_settings = context.scene.tool_settings

        clip = context.scene.active_clip
        tracks = getattr(getattr(clip, "tracking", None), "tracks", None)
        track_active = tracks.active if tracks else None
        pie = layout.menu_pie()
        editmode = context.object.mode == 'EDIT'

        # set origin to selection in Edit Mode, set origin to cursor in Object mode
        if context.active_object:
            # Origin to Geometry
            if editmode:
                pie.operator("object.origin_set", text="Origin to Geometry").type="ORIGIN_GEOMETRY"
            else:
                pie.operator("object.origin_to_geometry")

            # Origin to Cursor / Selected
            if editmode:
                pie.operator("object.origin_to_selected")
            else:
                pie.operator("object.origin_set", text="Origin to Cursor").type="ORIGIN_CURSOR"

        pie.operator("view3d.snap_cursor_to_selected", icon="CURSOR")
        pie.operator(
            "view3d.snap_selected_to_cursor",
            text="Selection to Cursor",
            icon='RESTRICT_SELECT_OFF',
        ).use_offset = False

        pie.operator("view3d.snap_cursor_to_center", icon="CURSOR")
        if track_active:
            if editmode:
                pie.operator("object.origin_to_marker")
            else:
                pie.operator("object.object_to_marker")

        pie.operator("scene.toggle_pivot")



########## REGISTER ############
classes = {
    VIEW3D_OT_toggle_pivot,
    VIEW3D_OT_origin_to_selected,
    VIEW3D_OT_origin_to_geometry,
    VIEW3D_OT_SetPivotIndividual,
    VIEW3D_OT_origin_to_marker,
    VIEW3D_OT_object_to_marker,
    VIEW3D_PIE_MT_snapping_pie,
}


def register():
    for c in classes:
        bpy.utils.register_class(c)

    wm = bpy.context.window_manager

    km = wm.keyconfigs.addon.keymaps.new(name = 'Object Mode')
    kmi = km.keymap_items.new('wm.call_menu_pie', 'S', 'PRESS', shift=True).properties.name = "VIEW3D_PIE_MT_snapping_pie"

    km = wm.keyconfigs.addon.keymaps.new(name = 'Mesh')
    kmi = km.keymap_items.new('wm.call_menu_pie', 'S', 'PRESS',shift=True).properties.name = "VIEW3D_PIE_MT_snapping_pie"

    km = wm.keyconfigs.addon.keymaps.new(name = 'Curve')
    kmi = km.keymap_items.new('wm.call_menu_pie', 'S', 'PRESS',shift=True).properties.name = "VIEW3D_PIE_MT_snapping_pie"

    km = wm.keyconfigs.addon.keymaps.new(name = 'Armature')
    kmi = km.keymap_items.new('wm.call_menu_pie', 'S', 'PRESS',shift=True).properties.name = "VIEW3D_PIE_MT_snapping_pie" 

    km = wm.keyconfigs.addon.keymaps.new(name = 'Pose')
    kmi = km.keymap_items.new('wm.call_menu_pie', 'S', 'PRESS',shift=True).properties.name = "VIEW3D_PIE_MT_snapping_pie"



def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
    #bpy.ops.wm.call_menu_pie(name="mesh.mesh_operators")
