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


import bpy

from bpy.types import Panel
from bpy.app.translations import pgettext_iface as iface_
from bl_ui.utils import PresetPanel

from bpy.types import Operator, PropertyGroup
from bpy.props import FloatProperty, BoolProperty, PointerProperty
from mathutils import (
    Vector,
    Matrix,
)


def CLIP_spaces_walk(context, all_screens, tarea, tspace, callback, *args):
    screens = bpy.data.screens if all_screens else [context.screen]

    for screen in screens:
        for area in screen.areas:
            if area.type == tarea:
                for space in area.spaces:
                    if space.type == tspace:
                        callback(space, *args)


def CLIP_set_viewport_background(context, clip, clip_user):

    def check_camera_has_distortion(tracking_camera):
        if tracking_camera.distortion_model == 'POLYNOMIAL':
            return not all(k == 0 for k in (tracking_camera.k1,
                                            tracking_camera.k2,
                                            tracking_camera.k3))
        elif tracking_camera.distortion_model == 'DIVISION':
            return not all(k == 0 for k in (tracking_camera.division_k1,
                                            tracking_camera.division_k2))
        return False

    def set_background(cam, clip, user):
        bgpic = None

        for x in cam.background_images:
            if x.source == 'MOVIE_CLIP':
                bgpic = x
                break

        if not bgpic:
            bgpic = cam.background_images.new()

        bgpic.source = 'MOVIE_CLIP'
        bgpic.clip = clip
        bgpic.clip_user.proxy_render_size = user.proxy_render_size
        if check_camera_has_distortion(clip.tracking.camera):
            bgpic.clip_user.use_render_undistorted = True
        bgpic.use_camera_clip = False

        cam.show_background_images = True

    scene_camera = context.scene.camera
    if (not scene_camera) or (scene_camera.type != 'CAMERA'):
        return
    set_background(scene_camera.data, clip, clip_user)


def CLIP_camera_for_clip(context, clip):
    scene = context.scene
    camera = scene.camera

    for ob in scene.objects:
        if ob.type == 'CAMERA':
            for con in ob.constraints:
                if con.type == 'CAMERA_SOLVER':
                    cur_clip = scene.active_clip if con.use_active_clip else con.clip

                    if cur_clip == clip:
                        return ob

    return camera


def CLIP_findOrCreateCamera(context):
    scene = context.scene

    if scene.camera:
        return scene.camera

    cam = bpy.data.cameras.new(name="Camera")
    camob = bpy.data.objects.new(name="Camera", object_data=cam)
    scene.collection.objects.link(camob)

    scene.camera = camob

    camob.matrix_local = (
        Matrix.Translation((0.0, -2.5, 1.6)) @
        Matrix.Rotation(0.0, 4, 'Z') @
        Matrix.Rotation(0.0, 4, 'Y') @
        Matrix.Rotation(1.57079, 4, 'X')
    )

    return camob

def CLIP_setupCamera(context):
    sc = context.space_data
    clip = sc.clip
    tracking = clip.tracking

    camob = CLIP_findOrCreateCamera(context)
    cam = camob.data

    # Remove all constraints to be sure motion is fine.
    camob.constraints.clear()

    # Set the viewport background
    CLIP_set_viewport_background(context, sc.clip, sc.clip_user)

    # Append camera solver constraint.
    con = camob.constraints.new(type='CAMERA_SOLVER')
    con.use_active_clip = True
    con.influence = 1.0

    cam.sensor_width = tracking.camera.sensor_width
    cam.lens = tracking.camera.focal_length


class CLIP_OT_new_setup_camera(Operator):
    bl_idname = "clip.new_setup_camera"
    bl_label = "Setup Camera"
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        return sc.type == 'CLIP_EDITOR' and sc.clip

    def execute(self, context):
        CLIP_findOrCreateCamera(context)
        CLIP_setupCamera(context)
        return {'FINISHED'}


class CLIP_OT_new_set_active_clip(Operator):
    bl_label = "Set Active Clip"
    bl_idname = "clip.new_set_active_clip"

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        return sc.type == 'CLIP_EDITOR' and sc.clip

    def execute(self, context):
        clip = context.space_data.clip
        scene = context.scene
        scene.active_clip = clip
        scene.render.resolution_x = clip.size[0]
        scene.render.resolution_y = clip.size[1]
        return {'FINISHED'}


class CLIP_OT_create_tracking_object(Operator):
    """Create an Empty Object in 3D viewport at position of active track"""
    bl_idname = "clip.create_tracking_object"
    bl_label = "Create Tracking Object"

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        solved_tracking_object = False
        if sc.type == 'CLIP_EDITOR' and sc.clip:
            tracking_object = sc.clip.tracking.objects.active
            if not tracking_object.is_camera:
                if tracking_object.reconstruction.is_valid:
                    solved_tracking_object = True
        
        return solved_tracking_object

    def execute(self, context):
        scene = context.scene
        sc = context.space_data
        clip = sc.clip

        tracking_object = sc.clip.tracking.objects.active
        active_track = tracking_object.tracks.active
        empty = bpy.data.objects.new(f'{tracking_object.name}_{active_track.name}', None)
        empty.empty_display_size = sc.clip.tracking.settings.object_distance/2
        empty.empty_display_type = 'SPHERE'
        bpy.data.collections["foreground"].objects.link(empty)

        con = empty.constraints.new(type='OBJECT_SOLVER')
        con.use_active_clip = True
        con.camera = context.scene.camera
        con.object = tracking_object.name
        con.influence = 1.0
        context.view_layer.objects.active = empty
        bpy.ops.constraint.objectsolver_set_inverse(constraint="Object Solver", owner='OBJECT')

        # get position
        matrix = Matrix.Identity(4)
        reconstruction = tracking_object.reconstruction
        framenr = scene.frame_current - clip.frame_start + 1
        reconstructed_matrix = reconstruction.cameras.matrix_from_frame(frame=framenr)
        matrix = scene.camera.matrix_world @  reconstructed_matrix.inverted()
        bundle = active_track.bundle

        empty.matrix_world.translation = matrix @ bundle

        return {'FINISHED'}


class CLIP_OT_new_set_viewport_background(Operator):
    """Set current movie clip as a camera background in 3D Viewport """ \
        """(works only when a 3D Viewport is visible)"""

    bl_idname = "clip.new_set_viewport_background"
    bl_label = "Set as Background"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if context.space_data.type != 'CLIP_EDITOR':
            return False

        sc = context.space_data

        return sc.clip

    def execute(self, context):
        sc = context.space_data
        CLIP_set_viewport_background(context, sc.clip, sc.clip_user)

        return {'FINISHED'}


class CLIP_OT_new_setup_tracking_scene(Operator):
    """Prepare scene for compositing 3D objects into this footage"""
    # TODO: it will be great to integrate with other engines (other than Cycles)

    bl_idname = "clip.new_setup_tracking_scene"
    bl_label = "Setup Tracking Scene"
    bl_options = {'UNDO', 'REGISTER'}


    @classmethod
    def poll(cls, context):
        sc = context.space_data

        if sc.type != 'CLIP_EDITOR':
            return False

        clip = sc.clip

        return clip and clip.tracking.reconstruction.is_valid

    @staticmethod
    def _setupScene(context):
        scene = context.scene
        scene.active_clip = context.space_data.clip
        scene.render.use_motion_blur = True
        scene.render.film_transparent = True


    @staticmethod
    def _setupViewport(context):
        sc = context.space_data
        CLIP_set_viewport_background(context, sc.clip, sc.clip_user)


    @staticmethod
    def createCollection(context, collection_name):
        def collection_in_collection(collection, collection_to_query):
            """Return true if collection is in any of the children or """
            """grandchildren of collection_to_query"""
            for child in collection_to_query.children:
                if collection == child:
                    return True

                if collection_in_collection(collection, child):
                    return True

        master_collection = context.scene.collection
        collection = bpy.data.collections.get(collection_name)

        if collection and collection.library:
            # We need a local collection instead.
            collection = None

        if not collection:
            collection = bpy.data.collections.new(name=collection_name)
            master_collection.children.link(collection)
        else:
            # see if collection is in the scene
            if not collection_in_collection(collection, master_collection):
                master_collection.children.link(collection)

    def _setupCollections(self, context):
        def setup_collection_recursively(collections, collection_name, attr_name):
            for collection in collections:
                if collection.collection.name == collection_name:
                    setattr(collection, attr_name, True)
                    break
                else:
                    setup_collection_recursively(collection.children, collection_name, attr_name)

        collections = context.scene.collection.children

        self.createCollection(context, "foreground")
        if context.scene.use_shadow_catcher:
            self.createCollection(context, "shadow catcher")


    @staticmethod
    def _wipeDefaultNodes(tree):
        if len(tree.nodes) != 2:
            return False
        types = [node.type for node in tree.nodes]
        types.sort()

        if types[0] == 'COMPOSITE' and types[1] == 'R_LAYERS':
            while tree.nodes:
                tree.nodes.remove(tree.nodes[0])

    @staticmethod
    def _findNode(tree, type):
        for node in tree.nodes:
            if node.type == type:
                return node

        return None

    @staticmethod
    def _findOrCreateNode(tree, type):
        node = CLIP_OT_new_setup_tracking_scene._findNode(tree, type)

        if not node:
            node = tree.nodes.new(type=type)

        return node

    @staticmethod
    def _needSetupNodes(context):
        scene = context.scene
        tree = scene.node_tree

        if not tree:
            # No compositor node tree found, time to create it!
            return True

        for node in tree.nodes:
            if node.type in {'MOVIECLIP', 'MOVIEDISTORTION'}:
                return False

        return True

    @staticmethod
    def _offsetNodes(tree):
        for a in tree.nodes:
            for b in tree.nodes:
                if a != b and a.location == b.location:
                    b.location += Vector((40.0, 20.0))

    def _setupNodes(self, context):
        if not self._needSetupNodes(context):
            # Compositor nodes were already setup or even changes already
            # do nothing to prevent nodes damage.
            return

        # Enable backdrop for all compositor spaces.
        def setup_space(space):
            space.show_backdrop = True

        CLIP_spaces_walk(context, True, 'NODE_EDITOR', 'NODE_EDITOR',
                         setup_space)

        sc = context.space_data
        scene = context.scene
        scene.use_nodes = True
        tree = scene.node_tree
        clip = sc.clip

        need_stabilization = False

        # Remove all the nodes if they came from default node setup.
        # This is simplest way to make it so final node setup is correct.
        self._wipeDefaultNodes(tree)

        # Create nodes.
        rlayer_fg = self._findOrCreateNode(tree, 'CompositorNodeRLayers')
        composite = self._findOrCreateNode(tree, 'CompositorNodeComposite')

        movieclip = tree.nodes.new(type='CompositorNodeMovieClip')
        distortion = tree.nodes.new(type='CompositorNodeMovieDistortion')

        if need_stabilization:
            stabilize = tree.nodes.new(type='CompositorNodeStabilize2D')

        scale = tree.nodes.new(type='CompositorNodeScale')
        alphaover = tree.nodes.new(type='CompositorNodeAlphaOver')
        viewer = tree.nodes.new(type='CompositorNodeViewer')

        # Setup nodes.
        movieclip.clip = clip

        distortion.clip = clip
        distortion.distortion_type = 'UNDISTORT'

        if need_stabilization:
            stabilize.clip = clip

        scale.space = 'RENDER_SIZE'

        rlayer_fg.scene = scene
        rlayer_fg.layer = "View Layer"

        # Create links.
        tree.links.new(movieclip.outputs["Image"], distortion.inputs["Image"])

        if need_stabilization:
            tree.links.new(distortion.outputs["Image"],
                           stabilize.inputs["Image"])
            tree.links.new(stabilize.outputs["Image"], scale.inputs["Image"])
        else:
            tree.links.new(distortion.outputs["Image"], scale.inputs["Image"])

        tree.links.new(scale.outputs["Image"], alphaover.inputs[1])

        tree.links.new(rlayer_fg.outputs["Image"], alphaover.inputs[2])

        tree.links.new(alphaover.outputs["Image"], composite.inputs["Image"])
        tree.links.new(alphaover.outputs["Image"], viewer.inputs["Image"])

        # Place nodes.
        movieclip.location = Vector((-300.0, 350.0))

        distortion.location = movieclip.location
        distortion.location += Vector((200.0, 0.0))

        if need_stabilization:
            stabilize.location = distortion.location
            stabilize.location += Vector((200.0, 0.0))

            scale.location = stabilize.location
            scale.location += Vector((200.0, 0.0))
        else:
            scale.location = distortion.location
            scale.location += Vector((200.0, 0.0))

        alphaover.location = scale.location
        alphaover.location += Vector((250.0, -250.0))

        composite.location = alphaover.location
        composite.location += Vector((300.0, -100.0))

        viewer.location = composite.location
        composite.location += Vector((0.0, 200.0))

        # Ensure no nodes were created on the position of existing node.
        self._offsetNodes(tree)

    @staticmethod
    def _createMesh(collection, name, vertices, faces):
        from bpy_extras.io_utils import unpack_list

        mesh = bpy.data.meshes.new(name=name)

        mesh.vertices.add(len(vertices))
        mesh.vertices.foreach_set("co", unpack_list(vertices))

        nbr_loops = len(faces)
        nbr_polys = nbr_loops // 4
        mesh.loops.add(nbr_loops)
        mesh.polygons.add(nbr_polys)

        mesh.polygons.foreach_set("loop_start", range(0, nbr_loops, 4))
        mesh.polygons.foreach_set("loop_total", (4,) * nbr_polys)
        mesh.loops.foreach_set("vertex_index", faces)

        mesh.update()

        ob = bpy.data.objects.new(name=name, object_data=mesh)
        collection.objects.link(ob)

        return ob

    @staticmethod
    def _getPlaneVertices(half_size, z):

        return [(-half_size, -half_size, z),
                (half_size, -half_size, z),
                (half_size, half_size, z),
                (-half_size, half_size, z)]

    def _createGround(self, collection):
        vertices = self._getPlaneVertices(4.0, 0.0)
        faces = [0, 1, 2, 3]

        ob = self._createMesh(collection, "Ground", vertices, faces)
        ob["is_ground"] = True

        return ob

    @staticmethod
    def _findGround(context):
        scene = context.scene

        for ob in scene.objects:
            if ob.type == 'MESH' and "is_ground" in ob:
                return ob

        return None

    @staticmethod
    def _createLight():
        light = bpy.data.lights.new(name="Light", type='POINT')
        lightob = bpy.data.objects.new(name="Light", object_data=light)

        lightob.matrix_local = Matrix.Translation((4.076, 1.005, 5.904))

        return lightob

    def _createSampleObject(self, collection):
        vertices = self._getPlaneVertices(1.0, -1.0) + \
            self._getPlaneVertices(1.0, 1.0)
        faces = (0, 1, 2, 3,
                 4, 7, 6, 5,
                 0, 4, 5, 1,
                 1, 5, 6, 2,
                 2, 6, 7, 3,
                 3, 7, 4, 0)

        return self._createMesh(collection, "Cube", vertices, faces)

    def _setupObjects(self, context):

        def setup_shadow_catcher_objects(collection):
            """Make all the newly created and the old objects of a collection """ \
                """to be properly setup for shadow catch"""
            for ob in collection.objects:
                ob.cycles.is_shadow_catcher = True
                for child in collection.children:
                    setup_shadow_catcher_collection(child)

        scene = context.scene
        fg_coll = bpy.data.collections["foreground", None]

        # Ensure all lights are active on foreground and background.
        has_light = False
        has_mesh = False
        for ob in scene.objects:
            if ob.type == 'LIGHT':
                has_light = True
            elif ob.type == 'MESH' and "is_ground" not in ob:
                has_mesh = True

        # Create sample light if there is no lights in the scene.
        if not has_light:
            light = self._createLight()
            context.scene.collection.objects.link(light)
            # fg_coll.objects.link(light)
            # bg_coll.objects.link(light)

        # Create sample object if there's no meshes in the scene.
        if not has_mesh:
            ob = self._createSampleObject(fg_coll)

        # Create ground object if needed.
        if scene.use_shadow_catcher:
            bg_coll = bpy.data.collections["shadow catcher", None]
            print("now create a shadow objects")
            ground = self._findGround(context)
            if not ground:
                ground = self._createGround(bg_coll)

            # And set everything on background layer to shadow catcher.
            if hasattr(scene, "cycles"):
                setup_shadow_catcher_objects(bg_coll)

    def execute(self, context):
        self._setupScene(context)
        self._setupViewport(context)
        CLIP_findOrCreateCamera(context)
        CLIP_setupCamera(context)
        self._setupCollections(context)
        if context.scene.create_node_tree:
            self._setupNodes(context)
        self._setupObjects(context)

        return {'FINISHED'}


class CLIP_PT_new_tools_scenesetup(Panel):
    bl_space_type = 'CLIP_EDITOR'
    bl_region_type = 'TOOLS'
    bl_label = "New Scene Setup"
    bl_translation_context = bpy.app.translations.contexts.id_movieclip
    bl_category = "Solve"

    @classmethod
    def poll(cls, context):
        sc = context.space_data
        clip = sc.clip

        return clip and sc.view == 'CLIP' and sc.mode != 'MASK'

    def draw(self, _context):
        clip = _context.space_data.clip
        tracking = clip.tracking
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        scene = _context.scene

        col = layout.column(align=True)
        col.prop(scene.render, "engine", text="Engine")
        col = layout.column(heading="Setup", align=True)
        col.prop(_context.scene, "create_node_tree")
        row = col.row()
        row.active = not 'WORKBENCH' in scene.render.engine
        row.prop(_context.scene, "use_shadow_catcher")
        col = layout.column()
        col.operator("clip.new_set_viewport_background")
        col.operator("clip.new_setup_camera")
        col.operator("clip.new_setup_tracking_scene")
        col = layout.column()
        col.active = not clip.tracking.objects.active.is_camera
        col.operator("clip.create_tracking_object", text="Setup Object")


classes = (
    CLIP_OT_new_setup_camera,
    CLIP_OT_new_set_active_clip,
    CLIP_OT_new_set_viewport_background,
    CLIP_OT_new_setup_tracking_scene,
    CLIP_OT_create_tracking_object,
    CLIP_PT_new_tools_scenesetup
)
# Register everything
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.use_shadow_catcher = bpy.props.BoolProperty(
            name="Shadow Catcher",
            description="Create a shadow catcher object",
            default=False,
            )
    bpy.types.Scene.create_node_tree = bpy.props.BoolProperty(
            name="Nodes",
            description="Generate a node tree for compositing",
            default=False,
            )

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()
