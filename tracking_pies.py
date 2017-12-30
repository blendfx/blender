# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

bl_info = {
    "name": "Clip Editor Pies: Key: 'hotkey list Below'",
    "description": "Clip Editor Pies",
    "author": "Antony Riakiotakis, Sebastian Koenig",
    "version": (0, 1, 1),
    "blender": (2, 77, 0),
    "location": "Q, W, Shift W, E, Shift S, Shift A, Shift E",
    "warning": "",
    "wiki_url": "",
    "category": "Pie Menu"
    }

import bpy
from bpy.types import Menu, Operator
import tracking_tools
def get_marker_list(scene, tracks):
    '''
    Everytime the operator is executed, generate a dictionary with all tracks and
    their markers, if they are not too short and/or are selected
    '''
    marker_dict = {}

    for t in tracks:
        # only operate on selected tracks that are not hidden
        if t.select and not t.hide:
            # generate a list of all tracked frames
            list = []
            for i in range(scene.frame_start, scene.frame_end):
                # first clear the weight of the tracks
                t.keyframe_delete(data_path="weight", frame=i)
                if t.markers.find_frame(i):
                    list.append(i)
            # if the list is longer than 20, add the list and the track to a dict
            # (a shorter list wouldn't make much sense)
            if len(list) > 20:
                marker_dict[t] = list
    return marker_dict 


def select_zero_weighted_tracks(scene, tracks):
    current_frame = scene.frame_current
    for t in tracks:
        t.select = True
    for f in range(scene.frame_start, scene.frame_end):
        scene.frame_set(f)
        for t in tracks:
            if t.weight>0:
                t.select = False
    scene.frame_current = current_frame


def insert_keyframe(scene, fade_time, marker_dict):
    current_frame = scene.frame_current
    for track, list in marker_dict.items():
        # define keyframe_values
        frame1 = list[0]
        frame2 = list[0] + fade_time
        frame3 = list[-2] - fade_time
        frame4 = list[-2]
        # only key track start if it is not the start of the clip
        if frame1 - scene.frame_start > fade_time:
            track.weight = 0
            track.keyframe_insert(data_path="weight", frame=frame1)
            track.weight = 1
            track.keyframe_insert(data_path="weight", frame=frame2)
        # now set keyframe for weight 0 at the end of the track
        # but only if it doesnt go until the end of the shot
        if scene.frame_end - frame4+1 > fade_time:
            track.keyframe_insert(data_path="weight", frame=frame3)
            track.weight = 0
            track.keyframe_insert(data_path="weight", frame=frame4)
    scene.frame_set(current_frame)



##############################
# CLASSES
##############################


class CLIP_OT_select_zero_weighted(Operator):
    '''Select all tracks that have a marker weight of zero through the entire shot'''
    bl_idname = "clip.select_zero_weighted_tracks"
    bl_label = "Select Zero Weighted Tracks"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space.type == 'CLIP_EDITOR')

    def execute(self, context):
        tracks = context.space_data.clip.tracking.tracks
        select_zero_weighted_tracks(context.scene, tracks)
        return {'FINISHED'}


class CLIP_OT_weight_fade(Operator):
    '''Fade in the weight of selected markers'''
    bl_idname = "clip.fade_marker_weight"
    bl_label = "Fade Marker Weight"
    bl_options = {'REGISTER', 'UNDO'}

    fade_time = bpy.props.IntProperty(name="Fade Time",
            default=10, min=0, max=100)

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space.type == 'CLIP_EDITOR')

    def execute(self, context):
        scene = context.scene
        tracks = context.space_data.clip.tracking.tracks
        insert_keyframe(scene, self.fade_time, get_marker_list(scene, tracks))
        return {'FINISHED'}



class CLIP_PIE_refine_pie(Menu):
    # Refinement Options
    bl_label = "Refine Intrinsics"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space.type == 'CLIP_EDITOR') and space.clip

    def draw(self, context):
        clip = context.space_data.clip
        settings = clip.tracking.settings

        layout = self.layout
        pie = layout.menu_pie()
        pie.prop(settings, "refine_intrinsics", expand=True)


class CLIP_PIE_geometry_reconstruction(Menu):
    # Geometry Reconstruction
    bl_label = "Reconstruction"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        pie.operator("clip.bundles_to_mesh", icon='MESH_DATA')
        pie.operator("clip.track_to_empty", icon='EMPTY_DATA')


class CLIP_PIE_display_pie(Menu):
    # Display Options
    bl_label = "Marker Display"

    def draw(self, context):
        space = context.space_data

        layout = self.layout
        pie = layout.menu_pie()
        pie.prop(space, "show_names", text="Show Track Info", icon='WORDWRAP_ON')
        pie.prop(space, "show_disabled", text="Show Disabled Tracks", icon='VISIBLE_IPO_ON')
        pie.prop(space, "show_marker_search", text="Display Search Area", icon='VIEWZOOM')
        pie.prop(space, "show_marker_pattern", text="Display Pattern Area", icon='BORDERMOVE')


class CLIP_PIE_marker_pie(Menu):
    # Settings for the individual markers
    bl_label = "Marker Settings"

    def draw(self, context):
        clip = context.space_data.clip
        tracks = getattr(getattr(clip, "tracking", None), "tracks", None)
        track_active = tracks.active if tracks else None

        layout = self.layout
        pie = layout.menu_pie()
        # Use Location Tracking
        prop = pie.operator("wm.context_set_enum", text="Loc", icon='OUTLINER_DATA_EMPTY')
        prop.data_path = "space_data.clip.tracking.tracks.active.motion_model"
        prop.value = "Loc"
        # Use Affine Tracking
        prop = pie.operator("wm.context_set_enum", text="Affine", icon='OUTLINER_DATA_LATTICE')
        prop.data_path = "space_data.clip.tracking.tracks.active.motion_model"
        prop.value = "Affine"
        # Copy Settings From Active To Selected 
        pie.operator("clip.track_settings_to_track", icon='COPYDOWN')
        # Make Settings Default
        pie.operator("clip.track_settings_as_default", icon='SETTINGS')
        if track_active:
        # Use Normalization
            pie.prop(track_active, "use_normalization", text="Normalization")
        # Use Brute Force
            pie.prop(track_active, "use_brute", text="Use Brute Force")
        # Use The blue Channel
            pie.prop(track_active, "use_blue_channel", text="Blue Channel")
        # Match Either Previous Frame Or Keyframe        
            if track_active.pattern_match == "PREV_FRAME":
                prop = pie.operator("wm.context_set_enum", text="Match Previous", icon='KEYINGSET')
                prop.data_path = "space_data.clip.tracking.tracks.active.pattern_match"
                prop.value = 'KEYFRAME'
            else:
                prop = pie.operator("wm.context_set_enum", text="Match Keyframe", icon='KEY_HLT')
                prop.data_path = "space_data.clip.tracking.tracks.active.pattern_match"
                prop.value = 'PREV_FRAME'


class CLIP_PIE_tracking_pie(Menu):
    # Tracking Operators
    bl_label = "Tracking"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Track Backwards
        prop = pie.operator("clip.track_markers", icon='PLAY_REVERSE')
        prop.backwards = True
        prop.sequence = True
        # Track Forwards
        prop = pie.operator("clip.track_markers", icon='PLAY')
        prop.backwards = False
        prop.sequence = True
        # Disable Marker
        pie.operator("clip.disable_markers", icon='RESTRICT_VIEW_ON').action = 'TOGGLE'
        # Detect Features
        pie.operator("clip.detect_features", icon='ZOOM_SELECTED')
        # Clear Path Backwards
        pie.operator("clip.clear_track_path", icon='BACK').action = 'UPTO'
        # Clear Path Forwards
        pie.operator("clip.clear_track_path", icon='FORWARD').action = 'REMAINED'
        # Refine Backwards
        pie.operator("clip.refine_markers", icon='LOOP_BACK').backwards = True
        # Refine Forwards
        pie.operator("clip.refine_markers", icon='LOOP_FORWARDS').backwards = False


class CLIP_PIE_clipsetup_pie(Menu):
    # Setup the clip display options
    bl_label = "Clip and Display Setup"

    def draw(self, context):
        space = context.space_data

        layout = self.layout
        pie = layout.menu_pie()
        # Reload Footage
        pie.operator("clip.reload", text="Reload Footage", icon='FILE_REFRESH')
        # Prefetch Footage
        pie.operator("clip.prefetch", text="Prefetch Footage", icon='LOOP_FORWARDS')
        # Mute Footage
        pie.prop(space, "use_mute_footage", text="Mute Footage", icon='MUTE_IPO_ON')
        # Render Undistorted
        pie.prop(space.clip_user, "use_render_undistorted", text="Render Undistorted")
        # Set Scene Frames
        pie.operator("clip.set_scene_frames", text="Set Scene Frames", icon='SCENE_DATA')
        # PIE: Marker Display
        pie.operator("wm.call_menu_pie", text="Marker Display", icon='PLUS').name = "CLIP_PIE_display_pie"
        # Set Active Clip
        pie.operator("clip.set_active_clip", icon='CLIP')
        # Lock Selection
        pie.prop(space, "lock_selection", icon='LOCKED')


class CLIP_PIE_solver_pie(Menu):
    # Operators to solve the scene
    bl_label = "Solving"

    def draw(self, context):
        clip = context.space_data.clip
        settings = getattr(getattr(clip, "tracking", None), "settings", None)

        layout = self.layout
        pie = layout.menu_pie()
        # create Plane Track
        pie.operator("clip.create_plane_track", icon='MESH_PLANE')
        # Solve Camera
        pie.operator("clip.solve_camera", text="Solve Camera", icon='OUTLINER_OB_CAMERA')
        # PIE: Refinement
        if settings:
            pie.operator("wm.call_menu_pie", text="Refinement",
                        icon='CAMERA_DATA').name = "CLIP_PIE_refine_pie"
        # Use Tripod Solver
            pie.prop(settings, "use_tripod_solver", text="Tripod Solver")
        # Set Keyframe A
        pie.operator("clip.set_solver_keyframe", text="Set Keyframe A",
                    icon='KEY_HLT').keyframe = 'KEYFRAME_A'
        # Set Keyframe B
        pie.operator("clip.set_solver_keyframe", text="Set Keyframe B",
                    icon='KEY_HLT').keyframe = 'KEYFRAME_B'
        # Clean Tracks
        prop = pie.operator("clip.clean_tracks", icon='STICKY_UVS_DISABLE')
        # Filter Tracks
        pie.operator("clip.filter_tracks", icon='FILTER')
        prop.frames = 15
        prop.error = 2


class CLIP_PIE_reconstruction_pie(Menu):
    # Scene Reconstruction
    bl_label = "Reconstruction"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Set Active Clip As Viewport Background
        pie.operator("clip.set_viewport_background", text="Set Viewport Background", icon='SCENE_DATA')
        # Setup Tracking Scene
        pie.operator("clip.setup_tracking_scene", text="Setup Tracking Scene", icon='SCENE_DATA')
        # Setup Floor
        pie.operator("clip.set_plane", text="Setup Floor", icon='MESH_PLANE')
        # Set Origin
        pie.operator("clip.set_origin", text="Set Origin", icon='MANIPUL')
        # Set X Axis
        pie.operator("clip.set_axis", text="Set X Axis", icon='AXIS_FRONT').axis = 'X'
        # Set Y Axis
        pie.operator("clip.set_axis", text="Set Y Axis", icon='AXIS_SIDE').axis = 'Y'
        # Set Scale
        pie.operator("clip.set_scale", text="Set Scale", icon='ARROW_LEFTRIGHT')
        # PIE: Reconstruction
        pie.operator("wm.call_menu_pie", text="Reconstruction",
                    icon='MESH_DATA').name = "CLIP_PIE_geometry_reconstruction"


class CLIP_PIE_timecontrol_pie(Menu):
    # Time Controls
    bl_label = "Time Control"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Jump To Startframe
        pie.operator("screen.frame_jump", text="Jump to Startframe", icon='TRIA_LEFT').end = False
        # Jump To Endframe
        pie.operator("screen.frame_jump", text="Jump to Endframe", icon='TRIA_RIGHT').end = True
        # Jump To Start Of The Track
        pie.operator("clip.frame_jump", text="Start of Track", icon='REW').position = 'PATHSTART'
        # Jump To End of The Track
        pie.operator("clip.frame_jump", text="End of Track", icon='FF').position = 'PATHEND'
        # Play Backwards
        pie.operator("screen.animation_play", text="Playback Backwards", icon='PLAY_REVERSE').reverse = True
        # Play Forwards
        pie.operator("screen.animation_play", text="Playback Forwards", icon='PLAY').reverse = False
        # Go One Frame Back
        pie.operator("screen.frame_offset", text="Previous Frame", icon='TRIA_LEFT').delta = -1
        # Go One Frame Forwards
        pie.operator("screen.frame_offset", text="Next Frame", icon='TRIA_RIGHT').delta = 1


class CLIP_PIE_tracking_tools(Menu):
    # Tracking Tools
    bl_label = "Tracking Tools"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Select Zero Weighted Tracks
        pie.operator("clip.select_zero_weighted_tracks", icon="GHOST_ENABLED")
        # Fade Marker Weight
        pie.operator("clip.fade_marker_weight", icon="SMOOTHCURVE")
        # Copy Color
        pie.operator("clip.track_copy_color", icon="COLOR")
        pie.operator("clip.filter_track_ends")
        pie.operator("clip.select_foreground")
        pie.operator("clip.clear_weight_animation")
        pie.operator("clip.weight_fade")

addon_keymaps = []

classes = (
    CLIP_OT_select_zero_weighted,
    CLIP_OT_weight_fade,
    CLIP_PIE_geometry_reconstruction,
    CLIP_PIE_tracking_pie,
    CLIP_PIE_display_pie,
    CLIP_PIE_marker_pie,
    CLIP_PIE_solver_pie,
    CLIP_PIE_refine_pie,
    CLIP_PIE_reconstruction_pie,
    CLIP_PIE_clipsetup_pie,
    CLIP_PIE_timecontrol_pie,
    CLIP_PIE_tracking_tools
)


def register():
    addon_keymaps.clear()
    for cls in classes:
        bpy.utils.register_class(cls)

    wm = bpy.context.window_manager

    if wm.keyconfigs.addon:

        km = wm.keyconfigs.addon.keymaps.new(name="Clip", space_type='CLIP_EDITOR')

        kmi = km.keymap_items.new("wm.call_menu_pie", 'Q', 'PRESS')
        kmi.properties.name = "CLIP_PIE_marker_pie"
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new("wm.call_menu_pie", 'W', 'PRESS')
        kmi.properties.name = "CLIP_PIE_clipsetup_pie"
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new("wm.call_menu_pie", 'E', 'PRESS')
        kmi.properties.name = "CLIP_PIE_tracking_pie"
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new("wm.call_menu_pie", 'S', 'PRESS', shift=True)
        kmi.properties.name = "CLIP_PIE_solver_pie"
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new("wm.call_menu_pie", 'W', 'PRESS', shift=True)
        kmi.properties.name = "CLIP_PIE_reconstruction_pie"
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new("wm.call_menu_pie", 'A', 'PRESS', shift=True)
        kmi.properties.name = "CLIP_PIE_timecontrol_pie"
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new("wm.call_menu_pie", 'E', 'PRESS', shift=True)
        kmi.properties.name = "CLIP_PIE_tracking_tools"
        addon_keymaps.append((km, kmi))


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
    addon_keymaps.clear()


if __name__ == "__main__":
    register()
