bl_info = {
"name": "Reconstructor",
"author": "Sebastian Koenig",
"version": (1, 0),
"blender": (2, 7, 9),
"location": "Clip Editor > Reconstructor",
"description": "Generate a plane from trackers",
"warning": "",
"wiki_url": "",
"tracker_url": "",
"category": "3D View"}

import bpy

#################################################
############## FUNCTIONS ########################
#################################################


class VIEW3D_OT_reconstruct_3d_plane(bpy.types.Operator):
    bl_idname = "clip.reconstruct_3d_plane"
    bl_label = "Reconstruct 3D Plane"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'CLIP_EDITOR'

    def execute(self, context):
        # make a mesh from selected markers, called "Tracks"
        bpy.ops.clip.bundles_to_mesh()

        # create a plane from the single vertices
        ob = bpy.data.objects["Tracks"]
        bpy.context.scene.objects.active = ob
        ob.select = True
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.edge_face_add()
        bpy.ops.object.mode_set(mode='OBJECT')
        # rename the object so that you can create new objects (called "Tracks")
        ob.name = "Trackermesh"
        return {'FINISHED'}





class CLIP_PT_scene_reconstruction(bpy.types.Panel):
    bl_idname = "clip.scene_reconstruction"
    bl_label = "Scene Reconstruction"
    bl_space_type = "CLIP_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Solve"

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.operator("clip.reconstruct_3d_plane")



########## REGISTER ############

def register():
    bpy.utils.register_class(VIEW3D_OT_reconstruct_3d_plane)
    bpy.utils.register_class(CLIP_PT_scene_reconstruction)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Clip', space_type='CLIP_EDITOR')
    kmi = km.keymap_items.new('clip.track_hooker', 'J', 'PRESS')



def unregister():

    bpy.utils.unregister_class(VIEW3D_OT_reconstruct_3d_plane)
    bpy.utils.unregister_class(CLIP_PT_scene_reconstruction)

if __name__ == "__main__":
    register()


