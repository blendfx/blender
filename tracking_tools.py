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
    "name": "Tracking Tools",
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
from mathutils import Vector

def get_marker_coordinates_in_pixels(context, track, frame_number):
    width, height = context.space_data.clip.size
    # return the marker coordinates in relation to the clip
    marker = track.markers.find_frame(frame_number)
    vector = Vector((marker.co[0] * width, marker.co[1] * height))
    return vector


def marker_velocity(context, track, frame):
    marker_a = get_marker_coordinates_in_pixels(context, track, frame)
    marker_b = get_marker_coordinates_in_pixels(context, track, frame-1)
    marker_velocity = marker_a - marker_b
    return marker_velocity


def get_difference(track_slope, average_slope, axis):
    # return the difference between slope of last frame and the average slope before it
    difference = track_slope[axis] - average_slope[axis]
    # rather use abs difference, to be able to better compare the actual value
    difference = abs(difference)
    return difference


def get_slope(context, track, frame):
    v1 = marker_velocity(context, track, frame)
    v2 = marker_velocity(context, track, frame-1)
    slope = v1-v2
    return slope


def check_eval_time(track, frame, eval_time):
    # check each frame for the evaluation time
    list = []
    for f in range(frame-eval_time, frame):
        # if there are no markers for that frame, skip
        if not track.markers.find_frame(f):
            continue
        # it also doesnt make sense to use a track that is has no previous marker
        if not track.markers.find_frame(f-1):
            continue
        # the frame after the last track is muted, but still valid, so skip that
        if track.markers.find_frame(f).mute:
             continue
        if track.markers.find_frame(f-1).mute:
             continue
        # append frames to the list 
        list.append(f)
        # make sure there are no gaps in the list
    if len(list) == eval_time:
        return True


def get_valid_tracks(scene, tracks):
    valid_tracks = {}
    for t in tracks:
        list = []
        for f in range(scene.frame_start, scene.frame_end):
            if not t.markers.find_frame(f):
                continue
            if t.markers.find_frame(f).mute:
                continue
            if not t.markers.find_frame(f-1):
                continue
            list.append(f)
            valid_tracks[t] = list
    return valid_tracks


def get_average_slope(context, track, frame, eval_time):
    average = Vector().to_2d()
    for f in range(frame-eval_time, frame):
        average = get_slope(context, track, f)
        average += average
    average = average / eval_time
    return average


def get_marker_list(scene, tracks, fade_time):
    # generate a dictionary of tracks that meet the needed conditions
    marker_dict = {}
    # minimum length should be twice the time we use to fade in/out
    threshold = fade_time * 2
    for t in tracks:
        # only operate on selected tracks that are not hidden
        if t.select and not t.hide:
            # generate a list of all tracked frames
            list = []
            for i in range(scene.frame_start, scene.frame_end):
                if t.markers.find_frame(i):
                    list.append(i)
            # if the list is longer than the threshold, add the list and the track to a dict
            # (a shorter list wouldn't make much sense)
            if len(list) > threshold:
                marker_dict[t] = list
    return marker_dict 


def clear_weight_animation(scene, tracks):
    zero_weighted = find_zero_weighted_tracks(scene, tracks)
    for t in tracks:
        if t.select and not t.hide:
            for i in range(scene.frame_start, scene.frame_end+1):
                try:
                    t.keyframe_delete(data_path="weight", frame=i)
                except:
                    pass
            # set the weight back to 1 unless it's a zero weighted track
            if not t in zero_weighted: 
                t.weight = 1


def find_zero_weighted_tracks(scene, tracks):
    current_frame = scene.frame_current
    list = []
    for t in tracks:
        list.append(t)
    for f in range(scene.frame_start, scene.frame_end):
        scene.frame_set(f)
        for t in list:
            if t.weight>0:
                list.remove(t)
    scene.frame_set(current_frame)
    return list



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


class CLIP_OT_filter_track_ends(Operator):
    '''Filter the Track for spikes at the end of a track'''
    bl_idname = "clip.filter_track_ends"
    bl_label = "Filter Track Ends"
    bl_options = {'REGISTER', 'UNDO'}
    
    eval_time = bpy.props.IntProperty(
        name="Evaluation Time",
        default=10,
        min=0,
        max=1000,
        description="The length of the last part of the track that should be filtered")

    threshold = bpy.props.IntProperty(
        name="Threshold",
        default=1,
        min=0,
        max=100,
        description="The threshold over which a marker is considered outlier")

    @staticmethod
    def filter_track_ends(context, threshold, eval_time):
        # compare the last frame's slope with the ones before, and if needed, mute it.
        tracks = context.space_data.clip.tracking.tracks
        valid_tracks = get_valid_tracks(context.scene, tracks)
        to_clean = {}
        for track, list in valid_tracks.items():
            f = list[-1] 
            # first get the slope of the current track on current frame
            track_slope = get_slope(context, track, f)
            # if the track is as long as the evaluation time, calculate the average slope
            if check_eval_time(track, f, eval_time):
                average_slope = Vector().to_2d()
                for i in range(f-eval_time, f):
                    # get the slopes of all frames during the evaluation time
                    av_slope = get_slope(context, track, i)
                    average_slope += av_slope 
                average_slope = average_slope / eval_time
                # check abs difference for both values in the vector
                for i in [0,1]:
                    # if the difference between average_slope and track_slope on any axis is above threshold,
                    # add to the to_clean dictionary
                    if not track in to_clean and get_difference(track_slope, average_slope, i) > threshold:
                        to_clean[track] = f
        # now we can disable the last frame of the identified tracks
        for track, frame in to_clean.items():
            print("cleaned ", track.name, "on frame ", frame)
            track.markers.find_frame(frame).mute=True
        return len(to_clean)
        @classmethod
        def poll(cls, context):
            sc = context.space_data
            return (sc.type == 'CLIP_EDITOR') and sc.clip

    def execute(self, context):
        # first do a minimal cleanup
        bpy.ops.clip.clean_tracks(frames=3, error=0, action='DELETE_TRACK')
        num_tracks = self.filter_track_ends(context, self.threshold, self.eval_time)
        self.report({'INFO'}, "Muted %d track ends" % num_tracks)
        return {'FINISHED'}


class CLIP_OT_select_foreground(Operator):
    '''Select Foreground Tracks with faster movement'''
    bl_idname = "clip.select_foreground_track"
    bl_label = "Select Foreground Tracks"
    bl_options = {'REGISTER', 'UNDO'}

    eval_time = bpy.props.IntProperty(
        name="Evaluation Time",
        default=20,
        min=0,
        max=1000,
        description="The length of the last part of the track that should be filtered")

    threshold = bpy.props.IntProperty(
        name="Threshold",
        default=2,
        min=0,
        max=100,
        description="The threshold over which a marker is considered outlier")

    @staticmethod
    def select_foreground(context, eval_time, threshold):
        # filter tracks that move a lot faster than others towards the end of the track
        tracks = context.space_data.clip.tracking.tracks
        valid_tracks = get_valid_tracks(context.scene, tracks)
        foreground = []
        for track, list in valid_tracks.items():
            f = list[-1]
            # first get the average of the last frame during evaluation time
            if check_eval_time(track, f, eval_time) and not track in foreground:
                track_average = get_average_slope(context, track, f, eval_time)
                # then get the average of all other tracks
                global_average = Vector().to_2d()
                currently_valid_tracks = []
                # first check if the other tracks are valid too.
                for t in tracks:
                    if check_eval_time(t, f, eval_time) and not t == track:
                        currently_valid_tracks.append(t)
                for t in currently_valid_tracks:
                    other_average = get_average_slope(context, t, f, eval_time)
                    global_average += other_average
                global_average = global_average / len(currently_valid_tracks)
                print(track.name, f, track_average, global_average)
                for i in [0,1]:
                    difference = get_difference(track_average, global_average, i) * eval_time
                    print(track.name, i, difference)
                    if difference > threshold:
                        foreground.append(track)
        for track in foreground:
            track.select = True

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        return (sc.type == 'CLIP_EDITOR') and sc.clip

    def execute(self, context):
        scene = context.scene
        self.select_foreground(context, self.eval_time, self.threshold)
        return {'FINISHED'}


class CLIP_OT_select_zero_weighted_tracks(Operator):
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
        zero_weighted = find_zero_weighted_tracks(scene, tracks)
        for t in zero_weighted:
            t.select = True
        return {'FINISHED'}


class CLIP_OT_weight_fade(Operator):
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
        # first clear any previous weight animation
        clear_weight_animation(scene, tracks)
        # then find out which tracks to operate on
        marker_dict = get_marker_list(scene, tracks, self.fade_time)
        # then insert the weight keyframes
        insert_keyframe(scene, self.fade_time, marker_dict)
        return {'FINISHED'}

class CLIP_OT_clear_weight_animation(Operator):
    '''Clear any weight animation of the selected tracks'''
    bl_idname = "clip.clear_weight_animation"
    bl_label = "Clear Weight Animation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (space.type == 'CLIP_EDITOR')

    def execute(self, context):
        scene = context.scene
        tracks = context.space_data.clip.tracking.tracks
        clear_weight_animation(scene, tracks)
        return {'FINISHED'}


class CLIP_PT_weight_fade_panel(Panel):
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
    CLIP_OT_weight_fade,
    CLIP_OT_select_foreground,
    CLIP_OT_filter_track_ends,
    CLIP_OT_clear_weight_animation,
    CLIP_OT_select_zero_weighted_tracks,
    CLIP_PT_weight_fade_panel
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
