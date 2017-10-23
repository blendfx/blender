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
    "name": "VRAIS Tools",
    "author": "Sebastian Koenig",
    "version": (1,0),
    "blender": (2, 77, 0),
    "location": "Properties > Render",
    "description": "Upload VR Panormas and Cubemaps to vrais.io",
    "warning": "",
    "wiki_url": "",
    "category": "Render"
    }


import bpy
import os
import http.client
from bpy.props import *
from math import radians
from bpy.types import Operator, AddonPreferences
from bpy.utils import register_class, unregister_class
from addon_utils import check


# ##########################################################
# CONFIGURE USER PREFS
# ##########################################################

class VraisTools(bpy.types.AddonPreferences):
    bl_idname = __name__

    vrais_key = StringProperty(name="VRAIS API KEY")

    def draw(self, context):
        layout = self.layout
        layout.label(text="Enter your vrais.io API key")
        layout.prop(self, "vrais_key")


# ##########################################################
# FUNCTIONS
# ##########################################################


# define the path of the resulting cubemap
def configure_vrais_cubemap_path(scn):
    vs = scn.vrais_settings
    suffix = ".jpg"
    vrais_cubemap_path = os.path.join(vs.cube_filepath, vs.filename + suffix)
    return vrais_cubemap_path

# create a new temporary scene, which is used to assemble the cubemap stripe from the 12 cubemap tiles. 
def create_new_scene(context):
    scn = context.scene
    size = scn.render.resolution_y
    res = scn.render.resolution_percentage

    hashes = [hash(s) for s in bpy.data.scenes]
    bpy.ops.scene.new(type='NEW')
    new_scn = [s for s in bpy.data.scenes if hash(s) not in hashes][0]
    new_scn.name = "vrais_tmp_scene"

    tree = new_scn.node_tree
    try:
        new_scn.view_settings.view_transform = 'sRGB'
    except:
        new_scn.view_settings.view_transform = 'Default'
    cam_data = scn.camera.data
    cam = bpy.data.objects.new("tmp_cam", cam_data)
    new_scn.objects.link(cam)
    render = new_scn.render
    render.resolution_x = size*12
    render.resolution_y = size
    render.resolution_percentage = res
    render.image_settings.file_format = "JPEG"
    render.filepath = configure_vrais_cubemap_path(scn)
    new_scn.use_nodes = True
    for n in new_scn.node_tree.nodes:
        new_scn.node_tree.nodes.remove(n)

    return new_scn


# create image nodes in the temporary scene
def img_node_creator(new_scn, scn):
    tree = new_scn.node_tree
    frame = str(scn.frame_current).zfill(4)
    file_format = scn.render.image_settings.file_format.lower()
    if file_format == "jpeg": # make sure the suffix matches the output
        file_format = "jpg"
    testlist = [] # this is used for testing if all images are found

    img_dict = {
        "EAST_%s_R" % (frame):1,     
        "WEST_%s_R" % (frame):2,     
        "ZENITH_%s_R" % (frame):3,     
        "NADIR_%s_R" % (frame):4,     
        "NORTH_%s_R" % (frame):5,     
        "SOUTH_%s_R" % (frame):6,
        "EAST_%s_L" % (frame):7,     
        "WEST_%s_L" % (frame):8,     
        "ZENITH_%s_L" % (frame):9,     
        "NADIR_%s_L" % (frame):10,     
        "NORTH_%s_L" % (frame):11,     
        "SOUTH_%s_L" % (frame):12      
        }
    # create new nodes with the images and names from 1 to 12.
    # with the node.name we pass the index on to the connector function
    for img in img_dict:
        img_path = os.path.join(scn.render.filepath, img + "." + file_format)
        img_index = img_dict[img]
        node = tree.nodes.new(type="CompositorNodeImage")
        node.location = node.location[0], node.location[1] -  img_index*300
        try:
            img_new = bpy.data.images.load(filepath=img_path)
            node.image = img_new
            node.name = str(img_index)
            testlist.append(img)
        except:
            print("there was a problem with the image path")
    pathcheck = len(testlist)==12
    # the pathcheck will return True only if there are really 12 cubemap tile images
    return pathcheck


# connect the 12 images with proper offset and size
def connector(new_scn, offset):
    tree = new_scn.node_tree
    nodes = tree.nodes
    links = tree.links
    res = new_scn.render.resolution_percentage
    offset = offset/100*res 
    center = -(offset*5)-(offset/2)

    # the first and last node need special treatment...
    for i in range(1,12):
        img_1 = nodes[str(i)]
        img_2 = nodes[str(i+1)]
        mix = nodes.new(type="CompositorNodeAlphaOver")
        if i == 1:
            tl_1 = nodes.new(type="CompositorNodeTransform")
            tl_1.location = img_1.location[0] + 100, img_1.location[1]
            tl_1.inputs['X'].default_value = center
            links.new(img_1.outputs[0], tl_1.inputs[0])
            links.new(tl_1.outputs[0], mix.inputs[1])

        tl = tree.nodes.new(type="CompositorNodeTransform")
        tl.inputs['X'].default_value = center + offset * i 
        tl.location = img_1.location[0] + 100, img_2.location[1]
        mix.location = tl.location[0] + 200, img_2.location[1] + 100
        links.new(img_2.outputs[0], tl.inputs[0])
        if not i ==1:
            links.new(img_1.outputs[0], mix.inputs[1])
        links.new(tl.outputs[0], mix.inputs[2])
        img_2.name = "old"
        mix.name = str(i+1)

    last_node = nodes['12']
    output = nodes.new(type="CompositorNodeComposite")
    output.location = last_node.location[0] + 200, last_node.location[1]
    links.new(last_node.outputs[0], output.inputs[0])


# upload the vr rendering to vrais.io
def vr_uploader(scn, path):
    filepath = path
    f = open(filepath, "rb")
    chunk = f.read()
    f.close()
    vs = scn.vrais_settings
    if scn.vrais_enum == 'VRAIS_CUBE':
        is_cubemap = "1"
    else:
        is_cubemap = "0"

    headers = {
        "Content-type": "multipart/form-data",
        "Accept": "text/plain",
        "Title": vs.vrais_title,
        "Description": vs.description,
        "Token": bpy.context.user_preferences.addons[__name__].preferences.vrais_key,
        "Convergence": str(scn.camera.data.stereo.convergence_distance),
        "IsCubemap": is_cubemap
        }

    conn = http.client.HTTPConnection("vrais.io")
    conn.request("POST", "/api.php?cmd=uploadItem", chunk, headers)
    response = conn.getresponse()
    remote_file = response.read()
    conn.close()
    print ("uploaded ", remote_file)
    return str(remote_file)


# check if the cubemap addon is enable in User Prefs
def check_cubemap_addon():
    addon = "render_cube_map"
    is_enabled, is_loaded = check(addon)
    if is_enabled:
        return True



# ##########################################################
# OPERATORS
# ##########################################################


class VRAIS_OT_setup_cubemap(bpy.types.Operator):
    """Setup render and camera parameters for a correct stereoscopic VR cubemap rendering"""
    bl_idname = "scene.vrais_setup_cubemap"
    bl_label = "Setup Cubemap"

    def execute(self, context):
        scn = context.scene
        render = scn.render
        cam_data = scn.camera.data

        render.engine = 'CYCLES'
        render.resolution_y = 1280 # recommended resolution for VRAIS
        render.resolution_x = render.resolution_y
        render.use_multiview = True
        render.image_settings.views_format = 'INDIVIDUAL'

        cam_data.type = 'PERSP'
        cam_data.angle = radians(90)

        try:
            cam_data.stereo.use_spherical_stereo = True
        except:
            self.report(
                {'ERROR'}, 
                "You seem to be using Blender 2.77 or lower, which does not support Spherical Stereo. Please consider upgrading to at least 2.78."
                )

        scn.vrais_enum = 'VRAIS_CUBE'
        scn.vrais_settings.cube_filepath = render.filepath

        if not check_cubemap_addon():
            self.report(
                {'ERROR'},
                "In order to render your VR scene as cubemap, you need to enable the 'Cube Map' add-on!")
        else:
            scn.cube_map.use_cube_map = True

        return {'FINISHED'}



class VRAIS_OT_setup_vr_panorama(bpy.types.Operator):
    """Setup render and camera parameters for a correct stereoscopic VR panorama rendering""" 
    bl_idname = "scene.vrais_setup_vr_panorama"
    bl_label = "Setup VR Panorama"

    def execute(self, context):
        scn = context.scene
        render = scn.render
        cam_data = scn.camera.data


        render.engine = 'CYCLES'
        render.resolution_y = 2048 # recommended resolution for VRAIS
        render.resolution_x = render.resolution_y * 2
        render.use_multiview = True
        render.image_settings.views_format = 'STEREO_3D'
        render.image_settings.stereo_3d_format.display_mode = "TOPBOTTOM"

        cam_data.cycles.panorama_type = 'EQUIRECTANGULAR'
        cam_data.type = 'PANO'
        
        try:
            cam_data.stereo.use_spherical_stereo = True
        except:
            self.report(
                {'ERROR'}, 
                "You seem to be using Blender 2.77 or lower, which does not support Spherical Stereo. Please consider upgrading to at least 2.78."
                )
            
        scn.vrais_enum = 'VRAIS_EQUI'
        scn.vrais_settings.equi_filepath = render.filepath

        return {'FINISHED'}



class VRAIS_OT_create_cubemap(bpy.types.Operator):
    """Create the cubemap stripe"""
    bl_idname = "scene.vrais_create_cubemap"
    bl_label = "Create Cubemap Stripe"

    def execute(self, context):
        scn = context.scene
        screen = context.screen
        new_scn = create_new_scene(context)
        if img_node_creator(new_scn, scn):
            connector(new_scn, scn.render.resolution_y)
            bpy.ops.render.render(write_still=True, scene = new_scn.name)
        else:
            self.report(
                {'ERROR'},
                "Couldn't load the cubemap tiles. Please check the render filepath."
                )
        bpy.data.scenes.remove(bpy.data.scenes[new_scn.name], do_unlink=True)
        context.screen.scene=bpy.data.scenes[scn.name]

        return {'FINISHED'}



class VRAIS_OT_uploader(bpy.types.Operator):
    """Upload to vrais.io"""
    bl_idname = "scene.vrais_uploader"
    bl_label = "Upload to vrais.io"

    def execute(self, context):
        scn = context.scene
        vs = scn.vrais_settings

        # check whether to upload panorama or cubemap
        if scn.vrais_enum == 'VRAIS_CUBE':
            path = bpy.path.abspath(configure_vrais_cubemap_path(scn))
        elif scn.vrais_enum == 'VRAIS_EQUI':
            path = bpy.path.abspath(vs.equi_filepath)

        # check if camera, title and description are setup correctly
        if not scn.camera.data.stereo.use_spherical_stereo:
            self.report(
                {'ERROR'}, 
                "Spherical Stereo was not enabled in camera settings. \
                This will lead to wrong stereo effect!"
                )
            return {'CANCELLED'}
        elif len(vs.description)==0:
            self.report(
                {'ERROR'}, 
                "Please fill in a description"
                )
            return {'CANCELLED'}
        elif len(vs.vrais_title)==0:
            self.report(
                {'ERROR'}, 
                "Please fill in a Title"
                )
            return {'CANCELLED'}
        elif len(context.user_preferences.addons[__name__].preferences.vrais_key)<2:
            self.report(
                {'ERROR'}, 
                "No VRAIS API key configured in Addon Preferences!"
                )
            return {'CANCELLED'}
        else:
            # if all is fine, upload the VR rendering
            self.report(
                {'INFO'},
                vr_uploader(scn, path)
                )

        return {'FINISHED'}
 


# ##########################################################
# UI
## ##########################################################


class RENDER_PT_vrais_tools(bpy.types.Panel):
    """Configure the VRAIS tools UI"""
    bl_idname = "scene.vrais_tools"
    bl_label = "VRAIS Tools"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        vs = scn.vrais_settings
        cubemap = scn.vrais_enum == 'VRAIS_CUBE'

        layout.label(text="Setup your VR Rendering")
        row = layout.row(align=True)
        row.operator("scene.vrais_setup_cubemap")
        row.operator("scene.vrais_setup_vr_panorama")

        layout.label(text="VRAIS upload configuration")
        col = layout.column()
        col.prop(scn, "vrais_enum", text="VR Type")
        col.prop(vs, 'vrais_title')
        col.prop(vs, 'description')
        if cubemap:
            col.prop(vs, 'cube_filepath')
            col.prop(vs, 'filename')
            col.operator("scene.vrais_create_cubemap", icon="IMAGE_DATA")
            col.operator("scene.vrais_uploader", text="Upload Cubemap", icon="FILE_TICK")
        else:
            col.prop(vs, 'equi_filepath')
            col.operator("scene.vrais_uploader", text="Upload VR Panorama", icon="FILE_TICK")



# ##########################################################
# PROPERTIES
# ##########################################################


class VraisSettings(bpy.types.PropertyGroup):
    vrais_title = StringProperty(
        name="Image Title",
        description="You need to fill in a title for the image to be displayed in VRAIS")
    description = StringProperty(
        name="Scene Description",
        description="You need to fill in a description for the image to be displayed in VRAIS")
    filename = StringProperty(
        name="Filename", 
        description="Set the name of the Cubemap Stripe, which will be generated and uploaded to VRAIS", 
        default="cubemap")
    equi_filepath = StringProperty(
        name="Filepath",
        description="Choose the VR Panorama File",
        subtype='FILE_PATH')
    cube_filepath = StringProperty(
        name="Filepath", 
        description="Here's where the Cubemap will be generated (and loaded)", 
        subtype='DIR_PATH')



# ##########################################################
# REGISTER
# ##########################################################


classes = (
    VraisTools,
    VraisSettings,
    VRAIS_OT_uploader,
    VRAIS_OT_setup_cubemap,
    VRAIS_OT_create_cubemap,
    VRAIS_OT_setup_vr_panorama,
    RENDER_PT_vrais_tools
    )

def register():
    for c in classes:
        register_class(c)

    bpy.types.Scene.vrais_settings = PointerProperty(type=VraisSettings)
    bpy.types.Scene.vrais_enum = bpy.props.EnumProperty(
        items=(
            ('VRAIS_CUBE','Cubemap','Cubemap Stripe', 1),
            ('VRAIS_EQUI','Equirectangular','Equirectangular Rendering', 2),
            )
        )

def unregister():
    for c in classes:
        unregister_class(c)

    del bpy.types.Scene.vrais_settings

if __name__ == "__main__":
    register()
