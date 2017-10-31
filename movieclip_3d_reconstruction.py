# -*- coding:utf-8 -*-

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  All rights reserved.
#
# ##### END GPL LICENSE BLOCK #####


bl_info = {
"name": "Reconstruct 3D Mesh",
"author": "Sebastian Koenig",
"version": (1, 0),
"blender": (2, 7, 9),
"location": "Clip Editor > Tools > Reconstruct 3D Mesh",
"description": "Generate a 3D mesh from trackers, works best for simple planes",
"warning": "",
"wiki_url": "",
"tracker_url": "",
"category": "Motion Tracking"}


import bpy

class CLIP_OT_mesh_reconstruction(bpy.types.Operator):
    ''' Create a face from selected tracks. Needs a camera solve. Works best for flat surfaces'''
    bl_idname = "clip.mesh_reconstruction"
    bl_label = "Mesh Reconstruction"
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == "CLIP_EDITOR"

    def execute(self, context):
        # make a mesh from selected markers, called "Tracks"
        bpy.ops.clip.bundles_to_mesh()

        # create a plane from the single vertices
        ob = bpy.data.objects["Tracks"]
        bpy.context.scene.objects.active = ob
        ob.select = True
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.edge_face_add()
        bpy.ops.object.mode_set(mode="OBJECT")
        # rename the object so that you can create new objects (called "Tracks")
        ob.name = "TrackMesh"
        return {'FINISHED'}


class CLIP_PT_mesh_reconstruction(bpy.types.Panel):
    bl_idname = "clip.mesh_reconstruction"
    bl_label = "Mesh Reconstruction"
    bl_space_type = "CLIP_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Solve"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.operator("clip.mesh_reconstruction")


########## REGISTER ############

def register():
    bpy.utils.register_class(CLIP_OT_mesh_reconstruction)
    bpy.utils.register_class(CLIP_PT_mesh_reconstruction)


def unregister():
    bpy.utils.unregister_class(CLIP_OT_mesh_reconstruction)
    bpy.utils.unregister_class(CLIP_PT_mesh_reconstruction)

if __name__ == "__main__":
    register()