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
    "location": "Viewport",
    "description": "Control Groups with a pie menu", 
    "warning": "",
    "wiki_url": "",
    "category": "Object"
    }

import bpy
from bpy.types import Menu
from bpy.types import Operator


def check_if_group(context):
    # return True only if the object is part of a group
    if len(context.active_object.users_group) > 0:
        return True

def check_if_empty(context):
    # check if the object is actually an Empty
    if context.active_object.type == 'EMPTY':
        return True

def group_items(self, context):
    items = [(g.name, g.name, g.name) for g in bpy.data.groups] 
    return items 

def assign_group(self, context):
    for ob in context.selected_objects:
        # if the group propery has not been written, set the group to None
        if not context.scene.group:
            ob.dupli_group = None
        else:
            # now that we know that there is scene.group, assign it to the active object
            group = bpy.data.groups[context.scene.group]
            ob.dupli_type = 'GROUP'
            ob.dupli_group = group


class VIEW3D_OT_DupliOffset(Operator):
    """Set offset used for DupliGroup based on cursor position"""
    bl_idname = "object.dupli_offset_from_cursor"
    bl_label = "Set Offset From Cursor"
    bl_options = {'REGISTER', 'UNDO'}

    # i copied this class from a blender UI script from the web, should be in blender/release somewhere
    group_index = bpy.props.IntProperty(
            name="Group",
            description="Group index to set offset for",
            default=0,
            )

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and check_if_group(context))

    def execute(self, context):
        scene = context.scene
        ob = context.active_object
        group = self.group_index

        ob.users_group[group].dupli_offset = scene.cursor_location
        return {'FINISHED'}


class VIEW3D_OT_NameGroupFromObject(Operator):
    ''' Set Group Name from Object Name (only if it's part of only 1 group)'''
    bl_idname = "object.name_group_from_object"
    bl_label = "GroupName from Object"

    @classmethod
    def poll(cls, context):
        return (context.object is not None and check_if_group(context))

    def execute(self, context):
        ob = context.active_object
        # Only if there is one group the object is part of, rename it
        if not len(ob.users_group) > 1:
            ob.users_group[0].name = ob.name
        return {'FINISHED'} 


class VIEW3D_OT_NameObjectFromGroup(Operator):
    ''' Set Object Name from Group Name (only it it's part of only 1 group)'''
    bl_idname = "object.name_object_from_group"
    bl_label = "ObjectName from Group"

    @classmethod
    def poll(cls, context):
        return (context.object is not None and check_if_group(context))

    def execute(self, context):
        # Only if there is one group the object is part of, rename it
        for ob in context.selected_objects:
            if not len(ob.users_group) > 1:
                ob.name = ob.users_group[0].name
        return {'FINISHED'} 



class VIEW3D_OT_AssignGroup(Operator):
    ''' Open a dialogue with Group Controls'''
    bl_label = "Group Select"
    bl_idname = "object.assign_group"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        return (context.object is not None and check_if_empty(context))

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


class VIEW3D_OT_SetGroupDrawType(Operator):
    bl_idname = "object.set_group_draw_size"
    bl_label = "Group Draw Size"

    @classmethod
    def poll(cls, context):
        return (context.object is not None)

    def execute(self, context):
        ob = context.active_object
        if ob.type == 'EMPTY':
            ob.empty_draw_size = 0.1
        return {'FINISHED'}


class VIEW3D_PIE_GroupingPies(Menu):
    bl_idname = "object.grouping_pies"
    bl_label = "Grouping Pies"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        pie.operator("object.select_linked", text="Select Same Object Data", icon='OBJECT_DATA').type='OBDATA'
        pie.operator("object.select_linked", text="Select Same Group", icon='GROUP').type='DUPGROUP'
        pie.operator("object.edit_linked", icon='LINK_BLEND')
        pie.operator("object.assign_group", text="Assign Group", icon='GROUP')
        pie.operator("object.dupli_offset_from_cursor", text="Offset from Cursor", icon='CURSOR')
        pie.operator("object.set_group_draw_size", icon='EMPTY_DATA')
        pie.operator("object.name_object_from_group", icon='OUTLINER_OB_GROUP_INSTANCE')
        pie.operator("object.name_group_from_object", icon='MESH_CUBE')



# ###########################################################
# REGISTER 
# ###########################################################


classes = (
        VIEW3D_OT_AssignGroup,
        VIEW3D_PIE_GroupingPies,
        VIEW3D_OT_DupliOffset,
        VIEW3D_OT_SetGroupDrawType,
        VIEW3D_OT_NameGroupFromObject,
        VIEW3D_OT_NameObjectFromGroup
        )

def register():
    for c in classes:
        bpy.utils.register_class(c)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name="Object Mode")
    kmi = km.keymap_items.new('wm.call_menu_pie', 'Y', 'PRESS', shift=True).properties.name = "object.grouping_pies"
    
    bpy.types.Scene.group = bpy.props.StringProperty()

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.group


if __name__ == "__main__":
    register()
