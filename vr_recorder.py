import logging
import os
from time import strftime, localtime

import bgl
import blf
import bpy
import bpy.utils.previews
from bpy.props import (BoolProperty, CollectionProperty, IntProperty,
                       StringProperty, PointerProperty)
from bpy.types import Operator, Panel, PropertyGroup, UIList

# from utils import draw_message

logger = logging.getLogger(os.path.basename(__file__))

RECORDING_CAM_NAME = 'Recording_cam'
DATE_FORMAT = '%d/%m/%y %H:%M:%S'
SHOT_COLLECTION = 'shots'


def draw_message(context, text, opacity=1.0, offset=0):
    bgl.glEnable(bgl.GL_BLEND)
    color = (1., 1., 1., 1.)
    blf.size(0, 6, 150)
    width = bpy.context.region.width
    start = width - blf.dimensions(0, text)[0] - 6
    # points = (
    #     (start, slotlower[slot]),
    #     (width - 2, slotlower[slot]),
    #     (width - 2, slotlower[slot] + slotheight - 4),
    #     (start, slotlower[slot] + slotheight - 4),
    # )
    # draw_2dpolygon(points, fillcolor=(*colors[msgtype], 0.2 * opacity))

    position = (start - 200, 100)
    # bgl.glBlendColor(*color)
    blf.position(0, *position, 0.25)
    blf.size(0, 14, 150)
    blf.draw(0, text)
    bgl.glEnable(bgl.GL_BLEND)


def shot_coll_available(context):
    collections = context.scene.collection.children
    if SHOT_COLLECTION not in collections:
        return False
    return True


def is_shot_selected(context):
    if not shot_coll_available(context):
        return False

    n_shots = len(context.scene.collection.children[SHOT_COLLECTION].objects)
    if n_shots == 0:
        return False

    if context.scene.vp_shot_list_index >= n_shots:
        return False

    return True


def stop_recording(scene):
    '''automatically stop recording when animation has reached the last frame'''
    if scene.frame_current > scene.frame_end:
        bpy.ops.scene.vp_stop_recording()
        logger.debug('Stopped playback.')


def get_active_shot_cam(scene):
    return scene.collection.children[SHOT_COLLECTION].objects[scene.vp_shot_list_index]


def create_shot_cam(context, shot_name):
    """ create shot camera object and add action if necessary """
    # create new camera object and camera data
    cam = bpy.data.objects.new(shot_name, bpy.data.cameras.new(shot_name))

    # every shot cam needs an action
    cam.animation_data_create()
    cam.data.animation_data_create()

    # create action to link animation data
    cam.animation_data.action = bpy.data.actions.new(shot_name + '_obj')
    cam.data.animation_data.action = bpy.data.actions.new(shot_name + '_cam')

    logger.debug(f"Created new shot cam '{shot_name}'.")
    return cam


def record_handler(scene, cam_ob, keytypes={'object': ['location', 'rotation_euler'],
                                            'camera': ['lens', 'dof.use_dof']}):
    ''' Write keyframes to action of the recording camera '''
    frame = scene.frame_current

    # get the object controlled by the tracker, to get its motion
    vp_cam = scene.camera
    cam_ob = get_active_shot_cam(scene)
    cam_cam = bpy.data.cameras[cam_ob.name]
    cam_ob.matrix_world = vp_cam.matrix_world

    # write keyframes to recording camera (need to be written separately for the object & camera
    # datablocks)
    for keytype in keytypes['object']:
        cam_ob.keyframe_insert(data_path=keytype, frame=frame)
    for keytype in keytypes['camera']:
        cam_cam.keyframe_insert(data_path=keytype, frame=frame)
    logger.debug(f'Wrote keyframes at frame {frame}.')


# TODO brainstorming: what other properties make up a shot
class VP_shot_info(PropertyGroup):
    '''Captures all relevant data beyond Blender internals that are needed for a shot'''
    name: StringProperty(
        name='ShotName',
        description='Name of the shot',
        default='shot'
    )
    rating: IntProperty(
        name='ShotRating',
        description='Rating of the shot',
        default=3,
        min=1,
        max=5
    )

    date: StringProperty(
        name='ShotDate',
        description='Date of shot recording',
        default=strftime(DATE_FORMAT, localtime())
    )

    amazing_prop: StringProperty(
        name='Sebis prop',
        description='An amazing new property that noone was expecting...',
        default='crazyfeature'
    )


class VP_UL_shot_list(UIList):
    '''List UI of recorded shots'''

    def draw_item(self, context, layout, data, shot_cam, icon, active_data, active_propname, index):
        custom_icon = 'CAMERA_DATA'

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if index == context.scene.get(active_propname):
                layout.prop(shot_cam, "name", text="", icon='OUTLINER_OB_CAMERA', emboss=False)
            else:
                layout.prop(shot_cam, "name", text="", icon=custom_icon, emboss=False)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon=custom_icon)


class VP_OT_add_shot(Operator):
    '''Add a new shot'''
    bl_idname = "scene.vp_add_shot"
    bl_label = "Add Shot"

    def execute(self, context):
        scene = context.scene
        shot_cam = create_shot_cam(context, scene.vp_shot_name)

        if SHOT_COLLECTION not in bpy.data.collections:
            shot_col = bpy.data.collections.new(SHOT_COLLECTION)
            logger.debug('Initialised shot collection.')
        else:
            shot_col = bpy.data.collections[SHOT_COLLECTION]

        if SHOT_COLLECTION not in scene.collection.children:
            scene.collection.children.link(shot_col)
            logger.debug('Added shot collection to scene.')

        # add shot camera, and initialise its animation properties
        context.scene.collection.children.get('shots').objects.link(shot_cam)
        shot_cam.animation_data_create()
        logger.info(f"Created new shot '{shot_cam.name}'.")
        return {'FINISHED'}


class VP_OT_play_shot(Operator):
    '''Play the selected shot'''
    bl_idname = "scene.vp_play_shot"
    bl_label = "Play Shot"

    @classmethod
    def poll(cls, context):
        return is_shot_selected(context)

    def modal(self, context, event):
        '''run modal until we cancel'''
        scene = context.scene
        context.area.tag_redraw()
        draw_message(context, 'playing vr recording...')
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}
        if scene.frame_current >= scene.frame_end:
            self.cancel(context)
            return {'FINISHED'}
        return {'PASS_THROUGH'}

    def cancel(self, context):
        '''cancel animation and remove contraints'''
        scene = context.scene
        bpy.ops.screen.animation_cancel(restore_frame=True)
        if stop_recording in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.remove(stop_recording)

        # set scene camera back to vp_camera
        scene.camera = self._vp_camera
        scene.camera.hide_viewport = False

        if self._draw_handler:
            bpy.types.SpaceView3D.draw_handler_remove(
                self._draw_handler, 'WINDOW')
            self._draw_handler = None

        return {'FINISHED'}

    def invoke(self, context, event):
        self._draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_message, (context, 'Playing shot...'), 'WINDOW', 'POST_PIXEL'
        )
        bpy.app.handlers.frame_change_pre.append(stop_recording)

        scene = context.scene

        # get the camera of the selected shot
        shot_cam = get_active_shot_cam(scene)

        # initirate handler
        wm = context.window_manager
        wm.modal_handler_add(self)

        # store the vp camera for the reset after playing
        self._vp_camera = scene.camera
        self._vp_camera.hide_viewport = True

        # make shot camera the active camera
        scene.camera = shot_cam

        # start from frame one
        scene.frame_current = scene.frame_start

        # play animation
        bpy.ops.screen.animation_play()

        return {'RUNNING_MODAL'}


class VP_OT_delete_shot(Operator):
    '''Delete Selected Shot'''
    bl_idname = "scene.vp_delete_shot"
    bl_label = "Delete Shot"

    @classmethod
    def poll(cls, context):
        return is_shot_selected(context)

    def execute(self, context):
        index = context.scene.vp_shot_list_index
        shot_cam = get_active_shot_cam(context.scene)
        shot_name = shot_cam.name
        bpy.data.objects.remove(shot_cam)
        if index > 0:
            context.scene.vp_shot_list_index -= 1
        logger.info(f"Shot '{shot_name}' removed .")

        return{'FINISHED'}


class VIEW_3D_OT_toggle_dof(Operator):
    """Toggle depth of field on the VP Camera"""
    bl_idname = "scene.toggle_dof"
    bl_label = "Toggle Dof"

    @classmethod
    def poll(cls, context):
        return context.scene.camera

    def execute(self, context):
        cam = context.scene.camera.data
        cam.dof.use_dof = not cam.dof.use_dof
        return {'FINISHED'}


class VIEW_3D_OT_change_focus(Operator):
    """Change increase or decrease the focus of the camera"""
    bl_idname = "scene.change_focus"
    bl_label = "Change VP Focus"

    focus_direction: bpy.props.BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return context.scene.camera

    def execute(self, context):
        cam = context.scene.camera.data
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
        scene = context.scene

        if stop_recording in bpy.app.handlers.frame_change_pre:
            return False

        if scene.vp_action_overwrite:
            return is_shot_selected(context) and scene.camera

        return scene.camera

    def execute(self, context):
        scene = context.scene
        scene.frame_current = scene.frame_start
        bpy.app.handlers.frame_change_pre.append(stop_recording)

        # TODO is autokeying actually needed (we set them manually anyway...)
        scene.vp_autokeysetting = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = True

        # get the object controlled by the tracker, to get its motion
        vp_cam = scene.camera
        vp_cam.data.vp_shot_info.date = strftime(DATE_FORMAT, localtime())

        # make sure the VP camera doesn't have any keyframes,
        # they would interfere with the VR motion
        vp_cam.animation_data_clear()
        vp_cam.data.animation_data_clear()

        if not scene.vp_action_overwrite:
            bpy.ops.scene.vp_add_shot()

        cam_ob = get_active_shot_cam(scene)
        cam_ob.animation_data_clear()
        cam_ob.data.animation_data_clear()

        # play and handle recording
        bpy.ops.screen.animation_play()
        bpy.app.handlers.frame_change_post.append(record_handler)
        return {'FINISHED'}


class VIEW_3D_OT_vp_stop_recording(Operator):
    '''Stop recording and cancel animation'''
    bl_idname = "scene.vp_stop_recording"
    bl_label = "Stop VP Recorder"

    @classmethod
    def poll(cls, context):
        # TODO split the functionality of playback handlers and recording handlers
        return stop_recording in bpy.app.handlers.frame_change_pre

    def execute(self, context):
        scene = context.scene
        # TODO can be removed
        # cam_ob = bpy.data.objects.get("Camera_helper_Empty")

        # stop animation and remove handler
        bpy.ops.screen.animation_cancel(restore_frame=False)
        if record_handler in bpy.app.handlers.frame_change_post:
            bpy.app.handlers.frame_change_post.remove(record_handler)

        # set autokey back to what it was
        scene.tool_settings.use_keyframe_insert_auto = scene.vp_autokeysetting
        cam = context.scene.camera
        bpy.app.handlers.frame_change_pre.remove(stop_recording)

        logger.info(f'Stopped recording to {cam.name}')
        return {'FINISHED'}


class VIEW_3D_PT_vp_recorder(Panel):
    bl_label = "VP Recorder"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VR'
    bl_context = 'objectmode'

    # def draw_header(self, context):
    #     self.layout.label(icon_value=vr_icons['blendFXIcon'].icon_id)

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.template_ID(context.scene, 'camera', text='VP Camera')

        layout.prop(scene, "vp_action_overwrite")

        # TODO this could be handled by the object name?
        layout.prop(scene, "vp_shot_name")

        vp_cam = context.scene.camera
        if vp_cam:
            cam_data = vp_cam.data
            box = layout.box()
            box.label(text='Shot settings')
            box.prop(cam_data, 'lens')
            box.prop(cam_data.dof, "use_dof")
            box.prop(cam_data.vp_shot_info, "rating", text='Rating')
            box.prop(cam_data.vp_shot_info, "date", text='Date')
            box.prop(cam_data.vp_shot_info, "amazing_prop", text='Sebis property')

        row = layout.row(align=True)
        row.operator("scene.vp_start_recording", text="Start Recording", icon='REC')
        row.operator("scene.vp_stop_recording", text="Stop Recording", icon='HANDLETYPE_VECTOR_VEC')


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

        if shot_coll_available(context):
            layout.template_list("VP_UL_shot_list", "test", scene.collection.children['shots'],
                                 "objects", scene, "vp_shot_list_index")

        col = layout.column(align=True)
        col.operator("scene.vp_add_shot", icon='PLUS')
        col.operator("scene.vp_play_shot", icon='PLAY')
        col.operator("scene.vp_delete_shot", icon='X')


classes = (
    VP_shot_info,
    VP_UL_shot_list,
    VP_OT_play_shot,
    VP_OT_delete_shot,
    VP_OT_add_shot,
    VIEW_3D_OT_vp_start_recording,
    VIEW_3D_OT_toggle_dof,
    VIEW_3D_OT_vp_stop_recording,
    VIEW_3D_OT_change_focus,
    VIEW_3D_PT_vp_playback,
    VIEW_3D_PT_vp_recorder
)

addon_keymaps = []
pcolls = {}


def register():
    pcolls['vr_icons'] = bpy.utils.previews.new()

    script_path = bpy.context.space_data.text.filepath
    # load the blendFX logo as icon
    pcolls['vr_icons'].load("blendFX", os.path.join(
        script_path, "blendfxicon.png"), 'IMAGE')

    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.vp_shot_name = StringProperty(
        name="Shot name",
        default="shot",
        description="Name of the action"
    )
    bpy.types.Scene.vp_autokeysetting = BoolProperty(
        name="Use Autokey"
    )
    bpy.types.Scene.vp_action_overwrite = BoolProperty(
        name="Overwrite VP action",
        default=False,
        description="Overwrite VP action or create a new one"
    )
    bpy.types.Scene.vp_shot_list_index = IntProperty(
        name="Index of Shots",
        default=0
    )
    bpy.types.Camera.vp_shot_info = PointerProperty(type=VP_shot_info)

    # keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(
            "scene.vp_start_recording", type='J', value='PRESS')
        kmi = km.keymap_items.new(
            "scene.vp_stop_recording", type='L', value='PRESS')
        addon_keymaps.append((km, kmi))


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    del bpy.types.Scene.vp_shot_list
    del bpy.types.Scene.vp_shot_list_index
    del bpy.types.Camera.vp_shot_info
    bpy.utils.previews.remove(pcolls['vr_icons'])


if __name__ == "__main__":
    register()
