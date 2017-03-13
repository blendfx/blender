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
    "name": "Render Tweaker",
    "author": "Sebastian Koenig",
    "version": (1,1),
    "blender": (2, 77, 0),
    "location": "Properties > Render",
    "description": "Store Cycles rendersettings in render slots for easier tweaking",
    "warning": "",
    "wiki_url": "",
    "category": "Render"
    }


import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.utils import register_class, unregister_class

# ################################################
# FUNCTIONS ######################################
# ################################################


def cycles_exists():
    return hasattr(bpy.types.Scene, "cycles")

def get_slot_id():
    return bpy.data.images['Render Result'].render_slots.active_index

def enable_slot_recording():
    context.scene.record_settings = True

def return_proplist():
    proplist = [
    "aa_samples",
    "ao_bounces_render",
    "ao_samples",
    "blur_glossy",
    "caustics_reflective",
    "caustics_refractive",
    "dicing_rate",
    "diffuse_bounces",
    "diffuse_samples",
    "film_exposure",
    "film_transparent",
    "filter_type",
    "filter_width",
    "glossy_bounces",
    "glossy_samples",
    "light_sampling_threshold",
    "max_bounces",
    "max_subdivisions",
    "mesh_light_samples",
    "min_bounces",
    "motion_blur_position",
    "pixel_filter_type",
    "progressive",
    "rolling_shutter_type",
    "rolling_shutter_duration",
    "sample_clamp_direct",
    "sample_clamp_indirect",
    "sample_all_lights_indirect",
    "sample_all_lights_direct",
    "samples",
    "sampling_pattern",
    "transmission_bounces",
    "subsurface_samples",
    "transmission_samples",
    "transparent_max_bounces",
    "transparent_min_bounces",
    "use_square_samples",
    "use_transparent_shadows",
    "volume_bounces",
    "volume_max_steps",
    "volume_samples",
    "volume_step_size"
    ]
    return proplist


# save all visibly relevant cycles scene settings
def save_settings_to_storage(slot_id):
    context = bpy.context
    scene = context.scene
    proplist = return_proplist()

    # if the dict doesnt exist yet, create it.
    if not scene.get('renderslot_properties'):
        scene['renderslot_properties'] = {}
    renderslot_properties = scene['renderslot_properties']
    # get the active slot id (unless it is 8)
    if slot_id == 8:
        slot_id = str(slot_id)
    else:
        slot_id = str(get_slot_id())
    # create the dict for the slot
    slot_id_dict = {}
    # fill the dict with the properties
    for prop in proplist:
        slot_id_dict[prop] = getattr(context.scene.cycles, prop)
    # assign the prop dict to the slot id as value
    renderslot_properties[slot_id] = slot_id_dict


# load cycles render settings
def load_settings_from_storage(context, slot_id):
    scene = context.scene
    try:
        for s in bpy.data.scenes:
            if s.master_scene:
                master = s
        renderslot_properties = master.get('renderslot_properties')
        # find the active slot id
        if not slot_id == 8:
            slot_id = str(get_slot_id())
        else:
            slot_id = str(slot_id)
        # get the dict for that id
        prop_dict = renderslot_properties[slot_id]
        # read out the properties from the script and set them
        for prop in prop_dict:
            new_value = prop_dict[prop]
            setattr(scene.cycles, prop, new_value)
        return True
    except:
        return False



# if slot recording is enabled, save render settings from current slot
def slot_handler(scene):
    if scene.record_settings:
        save_settings_to_storage(0)



# ###########################################
# OPERATORS #################################
# ###########################################


class RENDER_TWEAKER_OT_save_main_rendersettings(bpy.types.Operator):
    '''Save the current render settings as main settings'''
    bl_idname = "scene.save_main_rendersettings"
    bl_label = "Save Main Rendersettings"

    def execute(self, context):
        scene = context.scene
        # Make this the only master scene
        # (There can be only one! ;)
        for s in bpy.data.scenes:
            if s == scene:
                s.master_scene = True
            else:
                s.master_scene = False
        # Save the settings to an artificial 9th slot
        save_settings_to_storage(8)
        return {'FINISHED'}



class RENDER_TWEAKER_OT_restore_main_rendersettings(bpy.types.Operator):
    '''Restore render settings from main settings'''
    bl_idname = "scene.restore_main_rendersettings"
    bl_label = "Restore Main Rendersettings"

    def execute(self, context):
        if not load_settings_from_storage(context,8):
            self.report({'ERROR'}, "Looks like you didn't save the main render setup yet!")
        return {'FINISHED'}



class RENDER_TWEAKER_OT_enable_slot_recording(bpy.types.Operator):
    ''' Enable render setting storing. Press Ctrl+J to restore Settings.'''
    bl_idname = "scene.enable_slot_recording"
    bl_label = "Record Render Settings"

    def execute(self, context):
        scene = context.scene
        if not scene.record_settings:
            scene.record_settings = True
            save_settings_to_storage(0)
        else:
            scene.record_settings = False
        return {'FINISHED'}



class RENDER_TWEAKER_OT_render_slot_restore(bpy.types.Operator):
    '''Restore render settings from render slot'''
    bl_idname = "scene.render_slot_restore"
    bl_label = "Restore Rendersettings"

    def execute(self, context):
        if not load_settings_from_storage(context, 0):
            self.report({'ERROR'}, "Looks like render slot recording was not enabled. (Image Editor > Header)")
        return {'FINISHED'}



# ####################################################
# UI #################################################
# ####################################################


class RENDER_TWEAKER_PT_slot_record(bpy.types.Header):
    bl_idname = "panel.render_tweaker_record"
    bl_label = "Slot Record"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "HEADER"

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        if scene.record_settings:
            layout.operator("scene.enable_slot_recording", text="", icon="REC")
        else:
            layout.operator("scene.enable_slot_recording", text="", icon="RADIOBUT_OFF")



# Append Tweaker controls to Cycles Sampling Panel
def store_main_render_setup(self, context):
    scene = context.scene
    layout = self.layout
    multiscene = len(bpy.data.scenes)>1
    test = []
    for s in bpy.data.scenes:
        if s.master_scene:
            test.append(s)
    transfer_available = len(test)>0
    row = layout.row(align=True)
    row.operator("scene.save_main_rendersettings", text="Save Settings")
    row.operator("scene.restore_main_rendersettings", text="Restore Settings")


# #################################################
# #### REGISTER ###################################
# #################################################


classes = (
    RENDER_TWEAKER_OT_enable_slot_recording,
    RENDER_TWEAKER_OT_render_slot_restore,
    RENDER_TWEAKER_OT_save_main_rendersettings,
    RENDER_TWEAKER_OT_restore_main_rendersettings,
    RENDER_TWEAKER_PT_slot_record
    )

def register():
    for c in classes:
        register_class(c)

    bpy.app.handlers.render_complete.append(slot_handler)
    if cycles_exists():
        bpy.types.CyclesRender_PT_sampling.append(store_main_render_setup)

    bpy.types.Scene.record_settings = BoolProperty(
        name = "Record Render Settings",
        description="After eacher render save the render settings in current render slot",
        default=False)
    bpy.types.Scene.master_scene = BoolProperty(
        name = "Master Scene",
        description="When working with multiple scenes, make this the master scene to copy settings from",
        default=False)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Image', space_type='IMAGE_EDITOR')
    kmi = km.keymap_items.new('scene.render_slot_restore', 'J', 'PRESS', ctrl=True)



def unregister():
    for c in classes:
        unregister_class(c)

    if cycles_exists():
        bpy.types.CyclesRender_PT_sampling.remove(store_main_render_setup)

    if slot_handler in bpy.app.handlers.render_complete:
        bpy.app.handlers.render_complete.remove(slot_handler)


if __name__ == "__main__":
    register()