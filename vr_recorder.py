import bpy
from bpy.types import Operator, Panel

def stop_playback(scene):
    if scene.frame_current == scene.frame_end:
        bpy.ops.scene.vr_stop_recording()


def create_recorder_empty(context, name):
    """ create recorder object and create action if necessary """
    scene = context.scene
    # create object if necessary
    if not name in bpy.data.objects:
        object = bpy.data.objects.new(name, None)
    else:
        object = bpy.data.objects.get(name)

    # create action if necessary
    if not context.scene.vr_action_overwrite:
        if not object.animation_data:
            object.animation_data_create()
        action = bpy.data.actions.new(scene.vr_action_name)
        object.animation_data.action = action

    return object


def record_handler(scene, cam_ob):
    frame = scene.frame_current
    cam = bpy.data.objects.get(scene.recorded_object)
    cam_ob = bpy.data.objects.get("Camera_helper_Empty")
    cam_ob.location = cam.location
    cam_ob.rotation_euler = cam.rotation_euler
    cam_ob.keyframe_insert(data_path="location", frame=frame)
    cam_ob.keyframe_insert(data_path="rotation_euler", frame=frame)


class VIEW_3D_OT_toggle_dof(Operator):
    """Toggle depth of field on the VR Camera"""
    bl_idname = "scene.toggle_dof"
    bl_label = "Toggle Dof"

    @classmethod
    def poll(cls,context):
        return bpy.data.objects.get(context.scene.vr_camera)

    def execute(self, context):
        cam = bpy.data.objects.get(context.scene.vr_camera).data
        if not cam.dof.use_dof: 
            cam.dof.use_dof = True
        else:
            cam.dof.use_dof = False
        return {'FINISHED'}


class VIEW_3D_OT_change_focus(Operator):
    """Change increase or decrease the focus of the camera"""
    bl_idname = "scene.change_focus"
    bl_label = "Change VR Focus"

    focus_direction: bpy.props.BoolProperty(default=True)

    @classmethod
    def poll(cls,context):
        return bpy.data.objects.get(context.scene.vr_camera)

    def execute(self, context):
        cam = bpy.data.objects.get(context.scene.vr_camera).data
        focus_step = 3
        if not self.focus_direction:
            focus_step = -focus_step
        cam.lens += focus_step
        return {'FINISHED'}


class VIEW_3D_OT_vr_start_recording(Operator):
    """Assign a helper object, start playback and handle recording"""
    bl_idname = "scene.vr_start_recording"
    bl_label = "Start VR Recorder"

    @classmethod
    def poll(cls, context):
        return bpy.data.objects.get(context.scene.recorded_object)

    def execute(self, context):
        # store autokey
        scene = context.scene
        scene.frame_current = scene.frame_start
        scene.autokeysetting = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = True

        # get vr camera and clear animation
        cam = bpy.data.objects.get(context.scene.recorded_object)
        # assign or create the recorder object

        cam_ob = create_recorder_empty(context, "Camera_helper_Empty")
        if not scene.vr_action_overwrite:
            action = cam_ob.animation_data.action

        cam.animation_data_clear()
        # play and handle recording
        bpy.ops.screen.animation_play()
        bpy.app.handlers.frame_change_post.append(record_handler)
        return {'FINISHED'}


class VIEW_3D_OT_vr_stop_recording(Operator):
    bl_idname = "scene.vr_stop_recording"
    bl_label = "Stop VR Recorder"

    @classmethod
    def poll(cls, context):
        return bpy.data.objects.get(context.scene.recorded_object)

    def execute(self, context):
        scene = context.scene
        cam = bpy.data.objects.get(context.scene.recorded_object)
        cam_ob = bpy.data.objects.get("Camera_helper_Empty")
        # stop animation and remove handler
        bpy.ops.screen.animation_cancel(restore_frame=False)
        if record_handler in bpy.app.handlers.frame_change_post:
            bpy.app.handlers.frame_change_post.remove(record_handler)
        if not cam.animation_data:
            cam.animation_data_create()
        cam.animation_data.action = cam_ob.animation_data.action
        cam_ob.animation_data.action.use_fake_user = True
        # set autokey back to what it was
        scene.tool_settings.use_keyframe_insert_auto = scene.autokeysetting
        return {'FINISHED'}


class VIEW_3D_PT_vr_recorder(Panel):
    bl_label = "VR Recorder"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"
    bl_context = 'objectmode'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(scene, "vr_camera")
        layout.prop(scene, "vr_action_overwrite")
        layout.prop(scene, "vr_action_name")

        row = layout.row(align=True)
        row.label(text="Focus")
        row.operator("scene.change_focus", text="", icon="REMOVE").focus_direction = False
        row.operator("scene.change_focus", text="", icon="ADD").focus_direction = True
        row = layout.row()
        row.operator("scene.toggle_dof")
        row = layout.row(align=True)
        row.operator("scene.vr_start_recording", text="Start Recording")
        row.operator("scene.vr_stop_recording", text="Stop Recording")



classes = (
        VIEW_3D_OT_vr_start_recording,
        VIEW_3D_OT_toggle_dof,
        VIEW_3D_OT_vr_stop_recording,
        VIEW_3D_OT_change_focus,
        VIEW_3D_PT_vr_recorder
        )

addon_keymaps = []

def register():
    bpy.types.Scene.vr_action_name = bpy.props.StringProperty(
            name="Shot name",
            default="shot",
            description="Name of the action"
            )
    bpy.types.Scene.recorded_object = bpy.props.StringProperty(
            name="Recorded Object",
            default="Empty",
            description="Which Camera Object / Root is being recorded"
            )
    bpy.types.Scene.vr_camera = bpy.props.StringProperty(
            name="VR Camera",
            default="Camera.001",
            description="Which Camera Object / Root is being recorded"
            )
    bpy.types.Scene.autokeysetting = bpy.props.BoolProperty(
            name="Use Autokey"
            )
    bpy.types.Scene.vr_action_overwrite = bpy.props.BoolProperty(
            name="Overwrite VR action",
            default=True,
            description="Overwrite VR action or create a new one"
            )

    for c in classes:
        bpy.utils.register_class(c)

    bpy.app.handlers.frame_change_pre.append(stop_playback)

    # keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type= 'VIEW_3D')
        kmi = km.keymap_items.new("scene.vr_start_recording", type='J', value='PRESS')
        kmi = km.keymap_items.new("scene.vr_stop_recording", type='L', value='PRESS')
        addon_keymaps.append((km, kmi))



def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    bpy.app.handlers.frame_change_pre.remove(stop_playback)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


if __name__ == "__main__":
    register()
