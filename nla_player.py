import bpy
from bpy.types import Menu, Operator, Panel


class VP_OT_action_starter(Operator):
    bl_label = "Action Starter"
    bl_idname = "scene.action_starter"

    force_reset: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        if not self.force_reset:
            frame = bpy.context.scene.frame_current
        else:
            frame = 5000
        # OBJECTS
        for ob in bpy.data.objects:
            if  ob.pass_index == 10:
                continue
            if not ob.animation_data:
                continue
            if not ob.animation_data.action:
                continue
            for fcurve in ob.animation_data.action.fcurves:
                for point in fcurve.keyframe_points:
                    point.co.x = frame
            
        # LAMPS
        for l in bpy.data.lights:
            if not l.animation_data:
                continue
            if not l.animation_data.action:
                continue
            for fcurve in l.animation_data.action.fcurves:
                for point in fcurve.keyframe_points:
                    point.co.x = frame
        # SHAPEKEYS
        shapes = []
        for me in bpy.data.meshes:
            shapes.append(me)
        for me in bpy.data.curves:
            shapes.append(me)
        for me in shapes:
            if not me.shape_keys:
                continue
            if not me.shape_keys.animation_data:
                continue
            for fcurve in me.shape_keys.animation_data.action.fcurves:
                for point in fcurve.keyframe_points:
                    point.co.x = frame

        # SHADERNODES
        for ob in bpy.data.objects:
            if not ob.type == 'MESH':
                continue
            if not ob.data.materials:
                continue
            for mat in ob.data.materials:
                if not mat:
                    continue
                if not mat.use_nodes:
                    continue
                if not mat.node_tree.animation_data:
                    continue
                if not mat.node_tree.animation_data.action:
                    continue
                for fcurve in mat.node_tree.animation_data.action.fcurves:
                    for point in fcurve.keyframe_points:
                        point.co.x = frame

        return {'FINISHED'}


class VIEW_3D_PT_action_starter(Panel):
    bl_label = "Start Action"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VR'
    bl_context = 'objectmode'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        row = layout.row()
        col = row.column()
        ob = context.object
        col.operator("scene.action_starter").force_reset = False
        col.operator("scene.action_starter", text="Reset").force_reset = True

classes = (
        VP_OT_action_starter,
        VIEW_3D_PT_action_starter
        )

def register():
    for c in classes:
        bpy.utils.register_class(c)

    # keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type= 'VIEW_3D')
        # kmi = km.keymap_items.new("scene.action_starter", type='J', value='PRESS')
        # kmi = km.keymap_items.new("scene.vp_stop_recording", type='L', value='PRESS')
        # addon_keymaps.append((km, kmi))

def unregister():
    for c in classes:
        bpy.utils.unregister_class()

if __name__ == "__main__":
    register()

