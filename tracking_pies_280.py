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
    "version": (0, 1, 3),
    "blender": (2, 80, 0),
    "location": "E, Shift E, Shift D, Shift W, Shift S",
    "warning": "",
    "wiki_url": "",
    "category": "Pie Menu"
    }

import bpy
from bpy.types import Menu, Operator

##############################
# CLASSES
#
##############################


class CLIP_PIE_marker_pie(Menu):
    # Settings for the individual markers
    bl_label = "Marker Settings"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.mode == 'TRACKING'

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
            # Match Keyframe
            prop = pie.operator("wm.context_set_enum", text="Match Previous", icon='KEYFRAME_HLT')
            prop.data_path = "space_data.clip.tracking.tracks.active.pattern_match"
            prop.value = 'KEYFRAME'
            # Match Previous Frame
            prop = pie.operator("wm.context_set_enum", text="Match Keyframe", icon='KEYFRAME')
            prop.data_path = "space_data.clip.tracking.tracks.active.pattern_match"
            prop.value = 'PREV_FRAME'


class CLIP_PIE_tracking_pie(Menu):
    # Tracking Operators
    bl_label = "Tracking"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.mode == 'TRACKING'

    def draw(self, context):
        space = context.space_data
        clip = space.clip
        act_track = clip.tracking.tracks.active

        layout = self.layout
        pie = layout.menu_pie()
        # Track Backwards
        prop = pie.operator("clip.track_markers", icon='TRACKING_BACKWARDS')
        prop.backwards = True
        prop.sequence = True
        # Track Forwards
        prop = pie.operator("clip.track_markers", icon='TRACKING_FORWARDS')
        prop.backwards = False
        prop.sequence = True
        # Disable Marker
        pie.operator("clip.disable_markers", icon="VISIBLE_IPO_ON").action = 'TOGGLE'
        # Detect Features
        pie.operator("clip.detect_features", icon='ZOOM_SELECTED')
        # Clear Path Backwards
        pie.operator("clip.clear_track_path", icon='TRACKING_CLEAR_BACKWARDS').action = 'UPTO'
        # Clear Path Forwards
        pie.operator("clip.clear_track_path", icon='TRACKING_CLEAR_FORWARDS').action = 'REMAINED'
        # Refine Backwards
        pie.operator("clip.refine_markers", icon='TRACKING_REFINE_BACKWARDS').backwards = True
        # Refine Forwards
        pie.operator("clip.refine_markers", icon='TRACKING_REFINE_FORWARDS').backwards = False


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
        # Show Disabled Markers
        pie.prop(space, "show_disabled", text="Show Disabled Markers")
        # Set Scene Frames
        pie.operator("clip.set_scene_frames", text="Set Scene Frames", icon='SCENE_DATA')
        # Render Undistorted
        pie.prop(space.clip_user, "use_render_undistorted", text="Render Undistorted")
        # Lock Selection
        pie.prop(space, "lock_selection", icon='LOCKED')
        # Set Active Clip
        pie.operator("clip.set_active_clip", icon='CLIP')
        # Mute Footage
        pie.prop(space, "use_mute_footage", text="Mute Footage", icon='MUTE_IPO_ON')


class CLIP_PIE_solver_pie(Menu):
    # Operators to solve the scene
    bl_label = "Solving"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.mode == 'TRACKING'

    def draw(self, context):
        clip = context.space_data.clip
        settings = getattr(getattr(clip, "tracking", None), "settings", None)

        layout = self.layout
        pie = layout.menu_pie()
        # Clear Solution
        pie.operator("clip.clear_solution", icon='FILE_REFRESH')
        # Solve Camera
        pie.operator("clip.solve_camera", text="Solve Camera", icon='OUTLINER_OB_CAMERA')
        # Use Tripod Solver
        if settings:
            pie.prop(settings, "use_tripod_solver", text="Tripod Solver")
        # create Plane Track
        pie.operator("clip.create_plane_track", icon='MATPLANE')
        # Set Keyframe A
        pie.operator("clip.set_solver_keyframe", text="Set Keyframe A",
                    icon='KEYFRAME').keyframe = 'KEYFRAME_A'
        # Set Keyframe B
        pie.operator("clip.set_solver_keyframe", text="Set Keyframe B",
                    icon='KEYFRAME').keyframe = 'KEYFRAME_B'
        # Clean Tracks
        prop = pie.operator("clip.clean_tracks", icon='X')
        # Filter Tracks
        pie.operator("clip.filter_tracks", icon='FILTER')
        prop.frames = 15
        prop.error = 2


class CLIP_PIE_reconstruction_pie(Menu):
    # Scene Reconstruction
    bl_label = "Reconstruction"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.mode == 'TRACKING'

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        # Set Active Clip As Viewport Background
        pie.operator("clip.set_viewport_background", text="Set Viewport Background", icon='FILE_IMAGE')
        # Setup Tracking Scene
        pie.operator("clip.setup_tracking_scene", text="Setup Tracking Scene", icon='SCENE_DATA')
        # Setup Floor
        pie.operator("clip.set_plane", text="Setup Floor", icon='MESH_PLANE')
        # Set Origin
        pie.operator("clip.set_origin", text="Set Origin", icon='OBJECT_ORIGIN')
        # Set X Axis
        pie.operator("clip.set_axis", text="Set X Axis", icon='AXIS_FRONT').axis = 'X'
        # Set Y Axis
        pie.operator("clip.set_axis", text="Set Y Axis", icon='AXIS_SIDE').axis = 'Y'
        # Set Scale
        pie.operator("clip.set_scale", text="Set Scale", icon='ARROW_LEFTRIGHT')
        # Apply Solution Scale
        pie.operator("clip.apply_solution_scale", icon='ARROW_LEFTRIGHT')



addon_keymaps = []

classes = (
    CLIP_PIE_tracking_pie,
    CLIP_PIE_marker_pie,
    CLIP_PIE_solver_pie,
    CLIP_PIE_reconstruction_pie,
    CLIP_PIE_clipsetup_pie,
)


def register():
    addon_keymaps.clear()
    for cls in classes:
        bpy.utils.register_class(cls)

    wm = bpy.context.window_manager

    if wm.keyconfigs.addon:

        km = wm.keyconfigs.addon.keymaps.new(name="Clip", space_type='CLIP_EDITOR')

        kmi = km.keymap_items.new("wm.call_menu_pie", 'E', 'PRESS', shift=True)
        kmi.properties.name = "CLIP_PIE_marker_pie"
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new("wm.call_menu_pie", 'D', 'PRESS', shift=True)
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
