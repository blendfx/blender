import bpy
from bpy.types import Menu, Panel, Operator
import random
from mathutils import Vector
from numpy import mean
from math import sqrt

class VIEW3D_OT_cable_wizard(Operator):
    bl_idname = "object.cable_wizard"
    bl_label = "Cable Wizard"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create cables by vertex group"

    prevent_double = bpy.props.BoolProperty(
        name="Prevent Double Cables",
        description="Prevents two cables to spawn from the same vertices, it only makes sense to have this on when you have random gravity enabled",
        default = True)

    iterations = bpy.props.IntProperty(
            name="Iterations",
            default=20,
            min=1,
            description="Amount of cables to generate"
            )
    gravity = bpy.props.FloatProperty(
            name="Gravity",
            default=1.0,
            description="Defines the amount of hanging of the cable"
            )
    random_gravity = bpy.props.FloatProperty(
            name="Random Gravity",
            default=1.0,
            description="Defines the amount of hanging of the cable"
            )
    thickness = bpy.props.FloatProperty(
            name="Thickness",
            default=0.03,
            description="The maximum thickness of the cable"
            )
    random_thickness = bpy.props.FloatProperty(
            name="Random Thickness",
            default=0.03,
            description="The maximum thickness of the cable"
            )
    min_length = bpy.props.FloatProperty(
            name="Min Cable Length",
            default=2.0,
            description="The minimum length of a cable"
            )
    max_length = bpy.props.FloatProperty(
            name="Max Cable Length",
            default=50.0,
            description="The maximum length of a cable"
            )
    spread = bpy.props.FloatProperty(
            name="Spread",
            default=0.01,
            description="Move cable ends from the same source away from eachother"
            )
    @classmethod
    def poll(cls, context):
        if context.object.cable_source == "GREASE":
            return True
        elif not context.scene.vertex_group:
            return False
        return context.active_object is not None


    @staticmethod
    def make_poly_line(vector_list, thickness):
        # first create the data for the curve
        curvedata = bpy.data.curves.new(name="Cable", type='CURVE')
        curvedata.dimensions = '3D'
        curvedata.fill_mode = 'FULL'
        curvedata.bevel_resolution = 2
        curvedata.bevel_depth = thickness
        # then create a new object with our curvedata
        obj = bpy.data.objects.new("Cable", curvedata)
        obj.location = (0,0,0) #object origin
        #finally linkt it into our scene
        bpy.context.scene.objects.link(obj)
        # now fill the data with a spline
        polyline = curvedata.splines.new('NURBS')
        polyline.points.add(len(vector_list)-1)
        for i in range(len(vector_list)):
            polyline.points[i].co = vector_list[i]

        polyline.order_u = len(polyline.points)
        polyline.use_endpoint_u = True

    def generate_point(self ,coordinate):
        w=1
        point1 = coordinate[0] + (self.spread*random.uniform(-1,1)) 
        point2 = coordinate[1] + (self.spread*random.uniform(-1,1)) 
        point3 = coordinate[2] + (self.spread*random.uniform(-1,1)) 
        return (point1, point2, point3, w)

    def create_vector_list(self, context, thickness, rnd1_loc, rnd2_loc):
        random_gravity = self.gravity + self.random_gravity * random.uniform(0,1)
        spread = self.spread*random.uniform(-1,1)
        w = 1
        # contruct the position of the point in the middle
        mid_x = mean([rnd1_loc[0], rnd2_loc[0]]) + thickness * random.uniform(4,15)
        mid_y = mean([rnd1_loc[1], rnd2_loc[1]]) + thickness * random.uniform(4,15)
        mid_z = mean([rnd1_loc[2], rnd2_loc[2]]) - random_gravity
        # construct 4d Vectors with empty 4th value (w)
        mid_vert = (mid_x, mid_y, mid_z, w)
        rnd_vert_1 = self.generate_point(rnd1_loc)
        rnd_vert_2 = self.generate_point(rnd2_loc)
        # create a list with these 3 points
        vector_list = [rnd_vert_1, mid_vert, rnd_vert_2]
        return vector_list

    def get_grease_points(self, context):
        # grease pencil
        strokes = context.scene.grease_pencil.layers.active.active_frame.strokes

        rnd_stroke1 = random.choice(strokes)
        rnd_stroke2 = random.choice(strokes)

        point1 = rnd_stroke1.points
        point2 = rnd_stroke2.points

        rnd_point1 = random.choice(point1)
        rnd_point2 = random.choice(point2)

        rnd1 = rnd_point1.co
        rnd2 = rnd_point2.co
        return (rnd1, rnd2)

    def get_vertex_points(self, context):
        ob = context.active_object
        scene = context.scene
        v_group = ob.vertex_groups[scene.vertex_group]
        group_list = []
        group_index = v_group.index
        # find the vertices that are part of our group
        for v in ob.data.vertices:
            for g in v.groups:
                if g.group == group_index:
                    group_list.append(v)
        rnd1 = random.choice(group_list)
        rnd2 = random.choice(group_list)

        # defining w is needed to get a valid vector point for the curve vertices
        w = 1
        normal_local = rnd1.normal.to_4d()
        normal_local.w = 0
        normal_local = (ob.matrix_world * normal_local).to_3d()

        # get the absolute positions of the two random vertices
        pos = ob.matrix_world
        rnd1 = pos * rnd1.co
        rnd2 = pos * rnd2.co
        return (rnd1, rnd2)

    def execute(self, context):
        ob = context.active_object
        i=0
        while i < self.iterations:
            thickness = self.thickness + self.random_thickness * random.uniform(-1,1)
            if context.object.cable_source == "GREASE":
                rnd1 = self.get_grease_points(context)[0]
                rnd2 = self.get_grease_points(context)[1]
            elif context.object.cable_source == "VERTEX":
                rnd1 = self.get_vertex_points(context)[0]
                rnd2 = self.get_vertex_points(context)[1]

            distance = sqrt((rnd1[0]-rnd2[0])**2 + (rnd1[1]-rnd2[1])**2 +(rnd1[2]-rnd2[2])**2)
            if not distance < self.min_length and not distance > self.max_length:
                vector_list = self.create_vector_list(context, thickness, rnd1, rnd2)
                # now that we know the positions, create the cables
                self.make_poly_line(vector_list, thickness)
                # try to avoid creating the same curve twice during one iteration
                if self.prevent_double is True:
                    try:
                        point_list.remove(rnd1)
                        point_list.remove(rnd2)
                    except:
                        pass
            i+=1
        return {'FINISHED'}


class VIEW3D_OT_cable_edit(Operator):
    bl_idname = "object.cable_edit"
    bl_label = "Cable Edit"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Edit cables by created by Cable Wizard"

    gravity = bpy.props.FloatProperty(
            name="Gravity",
            default=0.0,
            description="Defines the amount of hanging of the cable"
            )
    random_gravity = bpy.props.FloatProperty(
            name="Random Gravity",
            default=0.0,
            description="Defines the amount of hanging of the cable"
            )
    thickness = bpy.props.FloatProperty(
            name="Thickness",
            default=0.0,
            min=0.0,
            description="The maximum thickness of the cable"
            )
    random_thickness = bpy.props.FloatProperty(
            name="Random Thickness",
            default=0.0,
            min=0.0,
            description="The maximum thickness of the cable"
            )
    @classmethod
    def poll(cls, context):
        for ob in context.selected_objects:
            if not ob.type == 'CURVE' or len(context.selected_objects)==0:
                return False
            else:
                return True

    def execute(self, context):
        obs = context.selected_objects
        for c in obs:
            thickness = self.thickness + self.random_thickness * random.uniform(-1,1)
            random_gravity = self.gravity + self.random_gravity * random.uniform(0,1)
            spline = c.data.splines[0]
            if len(spline.points) == 3:
               spline.points[1].co.z -= random_gravity
               c.data.bevel_depth = c.data.bevel_depth + thickness
        return {'FINISHED'}


class VIEW3D_PT_cable_wizard(Panel):
    bl_label = "Cable Wizard"
    bl_idname = "object.cable_wizard_menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Create"
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return context.active_object


    def draw(self, context):
        scn = context.scene
        ob = context.object

        layout = self.layout
        layout.label("Cable Source:")
        row = layout.row()
        row.prop(ob, "cable_source", expand=True)
        col = layout.column()
        # this is very hacky.
        # if an object without v_group is active, the group field shows red
        # looks like an error, even if it's not. 
        if ob.cable_source == 'VERTEX' and ob.type == 'MESH':
            col.prop_search(scn, "vertex_group", context.active_object, "vertex_groups", text="")
        col.label("Create Cables")
        col.operator("object.cable_wizard", icon="IPO_EASE_IN")
        col.label("Edit Cables")
        col.operator("object.cable_edit")




classes = (
    VIEW3D_OT_cable_wizard,
    VIEW3D_OT_cable_edit,
    VIEW3D_PT_cable_wizard,
        )

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.vertex_group = bpy.props.StringProperty(name="vertex_group")

    bpy.types.Object.cable_source = bpy.props.EnumProperty(
    items=(
        ('VERTEX', "Vertex Group", ""),
        ('GREASE', "Grease Pencil", ""),
    ),
    default='VERTEX'
    )
def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    del bpy.types.Scene.vertex_group
    del bpy.types.Object.cable_source

if __name__== "__main__":
    register()
