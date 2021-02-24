import bpy
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty
from bpy.types import Operator, Panel, UIList, PropertyGroup



def stop_recording(scene):
    if scene.frame_current == scene.frame_end:
        bpy.ops.scene.vp_stop_recording()


def create_recorder_empty(context, name):
    """ create recorder object and create action if necessary """
    scene = context.scene
    # create object if necessary
    if not name in bpy.data.objects:
        object = bpy.data.objects.new(name, None)
    else:
        object = bpy.data.objects.get(name)

    # create action if necessary
    if not context.scene.vp_action_overwrite:
        if not object.animation_data:
            object.animation_data_create()
        action = bpy.data.actions.new(scene.vp_action_name)
        object.animation_data.action = action
        print("animation_data is:", object.animation_data.action)
        object.animation_data.action.use_fake_user = True

    return object



def record_handler(scene, cam_ob):
    frame = scene.frame_current
    cam = bpy.data.objects.get(scene.recorded_object)
    cam_ob = bpy.data.objects.get("Camera_helper_Empty")
    cam_ob.location = cam.location
    cam_ob.rotation_euler = cam.rotation_euler
    cam_ob.keyframe_insert(data_path="location", frame=frame)
    cam_ob.keyframe_insert(data_path="rotation_euler", frame=frame)


def playback_handler(scene):
    frame = scene.frame_current
    cam = bpy.data.objects.get(scene.vp_camera)
    player = bpy.data.objects.get("player")
    cam.matrix_world = player.matrix_world



class ListItem(PropertyGroup):
    '''List of shot actions'''
    name:  StringProperty(
            name="ActionName",
            description="Name of the action",
            default="shot"
            )


class VP_UL_shot_list(UIList):
    '''List UI of shot actions'''
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        custom_icon = 'OBJECT_DATAMODE'

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", icon_value=icon, emboss=False)

        elif self.layout_type in {'GRID'}:
            layout.alignment='CENTER'
            layout.label(text="", icon=custom_icon)


class VP_OT_add_shot(Operator):
    '''Add Selected Shot'''
    bl_idname = "scene.add_vp_shot"
    bl_label = "Add VP Shot"

    def execute(self, context):
        context.object.vp_shot_list.add()
        return {'FINISHED'}


class VP_OT_play_shot(Operator):
    '''Play the selected shot'''
    bl_idname = "scene.vp_play_shot"
    bl_label = "Play Shot"

    @classmethod
    def poll(cls, context):
        return bpy.data.objects.get(context.scene.vp_camera)

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        wm.modal_handler_add(self)
        scene = context.scene
        index = context.object.vp_shot_list_index
        action = bpy.data.actions[index]
        print("playing ", action)
        cam = bpy.data.objects[scene.vp_camera]
        # store matrix
        self.cam_matrix = cam.matrix_world
        print(bpy.data.objects[context.scene.vp_camera].matrix_world)
        # if not cam.animation_data:
            # cam.animation_data_create()
        # print(cam.animation_data.action)
        # cam.animation_data.action = action

        scene = context.scene
        # create object if necessary
        if not "player" in bpy.data.objects:
            player = bpy.data.objects.new("player", None)
        else:
            player = bpy.data.objects.get("player")
        if not player.name in scene.collection.objects:
            scene.collection.objects.link(player)

        cam.animation_data_create()
        cam.animation_data.action = action

        bpy.ops.screen.animation_play()
        # bpy.app.handlers.frame_change_post.append(playback_handler)

        # cam.animation_data_clear()

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        scene = context.scene
        bpy.ops.screen.animation_cancel(restore_frame=False)
        cam = bpy.data.objects[scene.vp_camera]
        cam.animation_data_clear()
        print(bpy.data.objects[context.scene.vp_camera].location)
        bpy.data.objects[context.scene.vp_camera].matrix_world = self.cam_matrix
        # cam.animation_data_clear()

        return {'FINISHED'}


class VP_OT_delete_shot(Operator):
    '''Delete Selected Shot'''
    bl_idname = "scene.delete_item"
    bl_label = "Delete VP Shot"

    @classmethod
    def poll(cls, context):
        return context.object.vp_shot_list

    def execute(self, context):
        scene = context.scene
        index = context.object.vp_shot_list_index
        bpy.data.actions.remove(bpy.data.actions[index])

        return{'FINISHED'}


class VIEW_3D_OT_toggle_dof(Operator):
    """Toggle depth of field on the VP Camera"""
    bl_idname = "scene.toggle_dof"
    bl_label = "Toggle Dof"

    @classmethod
    def poll(cls,context):
        return bpy.data.objects.get(context.scene.vp_camera)

    def execute(self, context):
        cam = bpy.data.objects.get(context.scene.vp_camera).data
        if not cam.dof.use_dof: 
            cam.dof.use_dof = True
        else:
            cam.dof.use_dof = False
        return {'FINISHED'}


class VIEW_3D_OT_change_focus(Operator):
    """Change increase or decrease the focus of the camera"""
    bl_idname = "scene.change_focus"
    bl_label = "Change VP Focus"

    focus_direction: bpy.props.BoolProperty(default=True)

    @classmethod
    def poll(cls,context):
        return bpy.data.objects.get(context.scene.vp_camera)

    def execute(self, context):
        cam = bpy.data.objects.get(context.scene.vp_camera).data
        focus_step = 3
        if not self.focus_direction:
            focus_step = -focus_step
        cam.lens += focus_step
        return {'FINISHED'}


class VIEW_3D_OT_vp_start_recording(Operator):
    """Assign a helper object, start playback and handle recording"""
    bl_idname = "scene.vp_start_recording"
    bl_label = "Start VP Recorder"

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
        if not scene.vp_action_overwrite:
            action = cam_ob.animation_data.action
            bpy.ops.scene.add_vp_shot()

        cam.animation_data_clear()
        # play and handle recording
        bpy.ops.screen.animation_play()
        bpy.app.handlers.frame_change_post.append(record_handler)
        return {'FINISHED'}


class VIEW_3D_OT_vp_stop_recording(Operator):
    bl_idname = "scene.vp_stop_recording"
    bl_label = "Stop VP Recorder"

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

        # set autokey back to what it was
        scene.tool_settings.use_keyframe_insert_auto = scene.autokeysetting
        return {'FINISHED'}


class VIEW_3D_PT_vp_playback(Panel):
    bl_label = "VP Playback"
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
        col.template_list("VP_UL_shot_list", "", bpy.data, "actions", ob, "vp_shot_list_index")
        col.operator("scene.delete_item", text="REMOVE")
        col.operator("scene.vp_play_shot")
        # if scene.vp_shot_list_index >= 0 and scene.vp_shot_list:
            # item = scene.vp_shot_list[scene.vp_shot_list_index]

            # row = layout.row()
            # row.prop(item, "name")


class VIEW_3D_PT_vp_recorder(Panel):
    bl_label = "VP Recorder"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VR'
    bl_context = 'objectmode'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(scene, "vp_camera")
        layout.prop(scene, "recorded_object")
        layout.prop(scene, "vp_action_overwrite")
        layout.prop(scene, "vp_action_name")

        row = layout.row(align=True)
        row.label(text="Focus")
        row.operator("scene.change_focus", text="", icon="REMOVE").focus_direction = False
        row.operator("scene.change_focus", text="", icon="ADD").focus_direction = True
        row = layout.row()
        row.operator("scene.toggle_dof")
        row = layout.row(align=True)
        row.operator("scene.vp_start_recording", text="Start Recording")
        row.operator("scene.vp_stop_recording", text="Stop Recording")
        row.operator("scene.add_vp_shot", text="asdf")



classes = (
        ListItem,
        VP_UL_shot_list,
        VP_OT_play_shot,
        VP_OT_delete_shot,
        VP_OT_add_shot,
        VIEW_3D_OT_vp_start_recording,
        VIEW_3D_PT_vp_playback,
        VIEW_3D_OT_toggle_dof,
        VIEW_3D_OT_vp_stop_recording,
        VIEW_3D_OT_change_focus,
        VIEW_3D_PT_vp_recorder
        )

addon_keymaps = []

def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.vp_action_name = StringProperty(
            name="Shot name",
            default="shot",
            description="Name of the action"
            )
    bpy.types.Scene.recorded_object = StringProperty(
            name="Recorded Object",
            default="Empty",
            description="Which Camera Object / Root is being recorded"
            )
    bpy.types.Scene.vp_camera = StringProperty(
            name="VP Camera",
            default="",
            description="Which Camera Object / Root is being recorded"
            )
    bpy.types.Scene.autokeysetting = BoolProperty(
            name="Use Autokey"
            )
    bpy.types.Scene.vp_action_overwrite = BoolProperty(
            name="Overwrite VP action",
            default=True,
            description="Overwrite VP action or create a new one"
            )
    bpy.types.Object.vp_shot_list_index = IntProperty(
            name="Index of Shots",
            default=0
            )
    bpy.types.Object.vp_shot_list = CollectionProperty(
            type=ListItem
            )

    bpy.app.handlers.frame_change_pre.append(stop_recording)

    # keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type= 'VIEW_3D')
        kmi = km.keymap_items.new("scene.vp_start_recording", type='J', value='PRESS')
        kmi = km.keymap_items.new("scene.vp_stop_recording", type='L', value='PRESS')
        addon_keymaps.append((km, kmi))


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

    bpy.app.handlers.frame_change_pre.remove(stop_recording)
    bpy.app.handlers.frame_change_pre.remove(playback_handler)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    del bpy.types.Scene.vp_shot_list
    del bpy.types.Scene.vp_shot_list_index


if __name__ == "__main__":
    register()
