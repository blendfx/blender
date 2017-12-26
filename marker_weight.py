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

bl_info = {
    "name": "Fade Marker Weight",
    "author": "Sebastian Koenig",
    "version": (0,1),
    "blender": (2, 79, 0),
    "location": "Clip Editor",
    "description": "Fade in the weight of tracking markers to smooth out the camera path", 
    "warning": "",
    "wiki_url": "",
    "category": "Tracking"
    }

import bpy
from bpy.types import Operator, Panel

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



##############################
# CLASSES
##############################


class CLIP_OT_SelectZeroWeightedTracks(Operator):
    '''Select all tracks that have a marker weight of zero through the entire shot'''
    bl_idname = "clip.select_zero_weighted_tracks"
    bl_label = "Select Zero Weighted Tracks"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space.type == 'CLIP_EDITOR')

    def execute(self, context):
        scene = context.scene
        tracks = context.space_data.clip.tracking.tracks
        select_zero_weighted_tracks(scene, tracks)
        return {'FINISHED'}


class CLIP_OT_WeightFade(Operator):
    '''Fade in the weight of selected markers'''
    bl_idname = "clip.weight_fade"
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


class CLIP_PT_WeightFadePanel(Panel):
    bl_idname = "clip.weight_fade_panel"
    bl_label = "Weight Fade"
    bl_space_type = "CLIP_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Track"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.operator("clip.weight_fade")



###################
# REGISTER
###################

classes = (
    CLIP_OT_WeightFade,
    CLIP_OT_SelectZeroWeightedTracks,
    CLIP_PT_WeightFadePanel
    )

def register():
    for c in classes:
        bpy.utils.register_class(c)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Clip Editor', space_type='CLIP_EDITOR')
    kmi = km.keymap_items.new('clip.weight_fade', 'W', 'PRESS', alt=True)

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
