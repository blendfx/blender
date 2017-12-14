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

def get_marker_list(context):
    '''
    Everytime the operator is executed, generate a dictionary with all tracks and
    their markers, if they are not too short and/or are selected
    '''
    f_start = context.scene.frame_start
    f_end = context.scene.frame_end
    tracks = context.space_data.clip.tracking.tracks
    marker_dict = {}

    for t in tracks:
        # only operate on selected tracks that are not hidden
        if t.select and not t.hide:
            # generate a list of all tracked frames
            list = []
            for i in range(f_start, f_end):
                # first clear the weight of the tracks
                t.keyframe_delete(data_path="weight", frame=i)
                if t.markers.find_frame(i):
                    list.append(i)
            # if the list is longer than 20, add the list and the track to a dict
            # (a shorter list wouldn't make much sense)
            if len(list) > 20:
                marker_dict[t] = list
    return marker_dict 


def select_zero_weighted_tracks(context):
    f_start = context.scene.frame_start
    f_end = context.scene.frame_end
    tracks = context.space_data.clip.tracking.tracks

    current_frame = context.scene.frame_current
    for t in tracks:
        t.select = True
    for f in range(f_start, f_end):
        context.scene.frame_set(f)
        for t in tracks:
            if t.weight>0:
                t.select = False
    context.scene.frame_current = current_frame


def delete_weight_keyframes(context):
    f_start = context.scene.frame_start
    f_end = context.scene.frame_end
    tracks = context.space_data.clip.tracking.tracks

    for t in tracks:
        if t.select and not t.hide:
            for i in range(f_start, f_end):
                t.keyframe_delete(data_path="weight", frame=i)
                t.weight = 0


def insert_keyframe(context, fade_time, marker_dict):
    tracks = context.space_data.clip.tracking.tracks
    for track, list in marker_dict.items():
        # define keyframe_values
        frame1 = list[0]
        frame2 = list[0] + fade_time
        frame3 = list[-2] - fade_time
        frame4 = list[-2]
        # only key track start if it is not the start of the clip
        if frame1 - context.scene.frame_start > fade_time:
            track.weight = 0
            track.keyframe_insert(data_path="weight", frame=frame1)
            track.weight = 1
            track.keyframe_insert(data_path="weight", frame=frame2)
        # now set keyframe for weight 0 at the end of the track
        # but only if it doesnt go until the end of the shot
        if context.scene.frame_end - frame4+1 > fade_time:
            track.keyframe_insert(data_path="weight", frame=frame3)
            track.weight = 0
            track.keyframe_insert(data_path="weight", frame=frame4)



##############################
# CLASSES
##############################
class CLIP_OT_ClearWeightKeyframes(Operator):
    '''Select all tracks that have a marker weight of zero through the entire shot'''
    bl_idname = "clip.clear_weight_keyframes"
    bl_label = "Clear Weight Keyframes"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space.type == 'CLIP_EDITOR')

    def execute(self, context):
        delete_weight_keyframes(context)
        return {'FINISHED'}


class CLIP_OT_SelectZeroWeightedTracks(Operator):
    '''Select all tracks that have a marker weight of zero through the entire shot'''
    bl_idname = "clip.select_zero_weighted_tracks"
    bl_label = "Select Zero Weighted Tracks"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space.type == 'CLIP_EDITOR')

    def execute(self, context):
        select_zero_weighted_tracks(context)
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
        insert_keyframe(context, self.fade_time, get_marker_list(context))
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

def register():
    bpy.utils.register_class(CLIP_OT_WeightFade)
    bpy.utils.register_class(CLIP_OT_SelectZeroWeightedTracks)
    bpy.utils.register_class(CLIP_OT_ClearWeightKeyframes)
    bpy.utils.register_class(CLIP_PT_WeightFadePanel)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Clip Editor', space_type='CLIP_EDITOR')
    kmi = km.keymap_items.new('clip.weight_fade', 'W', 'PRESS', alt=True)

def unregister():
    bpy.utils.unregister_class(CLIP_OT_WeightFade)
    bpy.utils.unregister_class(CLIP_OT_SelectZeroWeightedTracks)
    bpy.utils.unregister_class(CLIP_OT_ClearWeightKeyframes)
    bpy.utils.unregister_class(CLIP_PT_WeightFadePanel)

if __name__ == "__main__":
    register()
