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
    "name": "Grouping Pies",
    "author": "Sebastian Koenig",
    "version": (0,1),
    "blender": (2, 79, 0),
    "location": "Viewpor",
    "description": "Control Groups with a pie menu", 
    "warning": "",
    "wiki_url": "",
    "category": "Object"
    }

import bpy
from bpy.props import (IntProperty)
from bpy.types import Menu


# TODO: edit linked library
# TODO: change name based on object
# TODO: change object name based on group

def group_items(self, context):
    return [(g.name, g.name, g.name) for g in bpy.data.groups]

def assign_group(self, context):
    ob = context.active_object
    # if the group propery has not been written, set the group to None
    if not context.scene.group:
        ob.dupli_group = None
    else:
        # now that we know that there is scene.group, assign it to the active object
        g = bpy.data.groups[context.scene.group]
        ob.dupli_type = 'GROUP'
        ob.dupli_group = g

class VIEW3D_OT_DupliOffset(bpy.types.Operator):
    """Set offset used for DupliGroup based on cursor position"""
    bl_idname = "object.dupli_offset_from_cursor"
    bl_label = "Set Offset From Cursor"
    bl_options = {'REGISTER', 'UNDO'}

    # i copied this class from a blender UI script from the web, should be in blender/release somewhere
    group = IntProperty(
            name="Group",
            description="Group index to set offset for",
            default=0,
            )

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None)

    def execute(self, context):
        scene = context.scene
        ob = context.active_object
        group = self.group

        # check if there are any groups at all, otherwise there'll be an error
        if len(ob.users_group)>0:
            ob.users_group[group].dupli_offset = scene.cursor_location
        return {'FINISHED'}


class MaskChooser(bpy.types.Operator):
    ''' Open a dialogue with Group Controls'''
    bl_label = "Mask Chooser"
    bl_idname = "object.mask_chooser"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        return (context.object is not None)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        # Show the name of the active Group, if any
        ob = context.active_object
        if ob.dupli_group:
            current_group = context.active_object.dupli_group.name
        else:
            current_group = "No Group"
        # UI
        layout = self.layout
        layout.label(text=current_group)
        row = layout.row(align=True)
        # search the groups in bpy.data and then write it to scene.group
        row.prop_search(context.scene, "group", bpy.data, "groups")


    def execute(self, context):
        assign_group(self, context)
        return {'FINISHED'}



class VIEW3D_PIE_GroupingPies(Menu):
    bl_idname = "object.grouping_pies"
    bl_label = "Grouping Pies"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        pie.operator("object.dupli_offset_from_cursor", text="Offset from Cursor")
        pie.operator("object.mask_chooser", text="Mask Chooser")




# ###########################################################
# REGISTER 
# ###########################################################


classes = (
        MaskChooser,
        VIEW3D_PIE_GroupingPies,
        VIEW3D_OT_DupliOffset,
         )

def register():
    for c in classes:
        bpy.utils.register_class(c)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name="Object Mode")
    kmi = km.keymap_items.new('wm.call_menu_pie', 'Y', 'PRESS', shift=True).properties.name = "object.grouping_pies"
    #kmi = km.keymap_items.new('object.grouping_pies', 'Y', 'PRESS', shift=True)
    
    bpy.types.Scene.group = bpy.props.StringProperty()

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.group


if __name__ == "__main__":
    register()
