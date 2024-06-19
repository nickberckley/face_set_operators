import bpy, bmesh, random


#### ------------------------------ FUNCTIONS ------------------------------ ####

def ensure_face_sets(mesh):
    if ".sculpt_face_set" not in mesh.attributes:
        mesh.attributes.new(".sculpt_face_set", 'INT', 'FACE')
    attribute = mesh.attributes[".sculpt_face_set"].data

    # get_face_set_index
    face_set_index = {}
    for i, face_set_data_value in enumerate(set(data.value for data in attribute)):
        face_set_index[face_set_data_value] = i

    return attribute, face_set_index


def create_copy_atribute(mesh, name):
    """Creates new attribute with same index and values as .sculot_face_set"""

    # create_new_attribute
    if name not in mesh.attributes:
        mesh.attributes.new(name=name, type='INT', domain='FACE')
    attribute = mesh.attributes[name].data

    # ensure_face_sets
    face_sets, face_set_index = ensure_face_sets(mesh)

    # transfer_face_set_index
    for i, face_set_data in enumerate(face_sets):
        attribute[i].value = face_set_index[face_set_data.value]
    values = [d.value for d in attribute]

    return attribute, values


def get_boundary_edges(bm):
    """Returns boundary edge loop for selected faces"""

    selected_faces = [f for f in bm.faces if f.select]

    boundary_edges = set()
    for face in selected_faces:
        for edge in face.edges:
            linked_faces = [f for f in edge.link_faces if f in selected_faces]
            if len(linked_faces) == 1:
                boundary_edges.add(edge)

    return boundary_edges


# def get_boundary_edges(mesh):
#     """Returns boundary edge loop for selected faces (Mesh verson)"""

#     from collections import defaultdict
#     selected_faces = {p.index for p in mesh.polygons if p.select}
#     edge_count = defaultdict(int)

#     for poly_index in selected_faces:
#         poly = mesh.polygons[poly_index]
#         for edge_key in poly.edge_keys:
#             edge_count[edge_key] += 1

#     boundary_edges = []
#     for edge in mesh.edges:
#         if edge_count[edge.key] == 1:
#             boundary_edges.append(edge)

#     return boundary_edges



#### ------------------------------ OPERATORS ------------------------------ ####

class SCULPT_OT_face_sets_to_materials(bpy.types.Operator):
    bl_idname = "sculpt.face_sets_to_materials"
    bl_label = "Face Sets to Materials"
    bl_description = ("Transfer the face set index to the material index.\n"
                    "Will create new material slot with empty node-less material for each face set.\n"
                    "WARNING: Material colors might blend in with face set colors in sculpt mode if Viewport Shading color is set to Material")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.mode == 'SCULPT'

    def execute(self, context):
        obj = context.sculpt_object
        mesh = obj.data

        # Create Attributes
        __, face_set_index = ensure_face_sets(mesh)
        create_copy_atribute(mesh, "material_index")

        # Add Material Slots
        slot_num = len(mesh.materials.values())
        for _ in range(len(face_set_index) - slot_num):
            bpy.ops.object.material_slot_add()

        # Create 'sculpt_face_set' Materials
        for mat_slot in obj.material_slots.values():
            if mat_slot.material == None:
                mat_slot.material = bpy.data.materials.new('Material')
                mat_slot.material.diffuse_color[0] = random.random()
                mat_slot.material.diffuse_color[1] = random.random()
                mat_slot.material.diffuse_color[2] = random.random()
                mat_slot.material.name = "sculpt_face_set"

        self.report({'INFO'}, "Material slots were created for each face set")
        return {'FINISHED'}


class SCULPT_OT_face_sets_to_vertex_groups(bpy.types.Operator):
    bl_idname = 'sculpt.face_sets_to_vertex_groups'
    bl_label = 'Face Sets to Vertex Groups'
    bl_description = "Creates Vertex Group for each Face Set"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.mode == 'SCULPT'

    def execute(self, context):
        obj = context.sculpt_object
        mesh = context.sculpt_object.data

        # Create Attributes
        attribute, values = create_copy_atribute(mesh, "face_sets")

        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(mesh)
        bpy.ops.mesh.select_all(action='DESELECT')

        # selection
        for target in range(max(values) + 1):
            for face, value in zip(bm.faces, values):
                if value == target:
                    face.select = True

            # Create Vertex Group
            group = obj.vertex_groups.new(name="face_sets.000")
            bpy.ops.object.vertex_group_assign()

            # deselect_again
            bpy.ops.mesh.select_all(action='DESELECT')

        bmesh.update_edit_mesh(mesh)
        bpy.ops.object.mode_set(mode='SCULPT')

        self.report({'INFO'}, "Vertex groups were created for each face set")
        return {'FINISHED'}


class SCULPT_OT_face_sets_to_attribute(bpy.types.Operator):
    bl_idname = 'sculpt.face_sets_to_attribute'
    bl_label = 'Face Sets to Attribute'
    bl_description = "Creates cached face sets attribute usable outside node tool contexts"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.mode == 'SCULPT'

    def execute(self, context):
        mesh = context.sculpt_object.data
        create_copy_atribute(mesh, "face_sets")

        self.report({'INFO'}, "'face_sets' attribute created")
        return {'FINISHED'}


class SCULPT_OT_face_sets_to_uv(bpy.types.Operator):
    bl_idname = 'sculpt.face_sets_to_uv'
    bl_label = 'Face Sets to UVMap'
    bl_description = "Creates UV islands from Face Set boundaries"
    bl_options = {'UNDO'}

    unwrap: bpy.props.BoolProperty(
        default = True,
        name = "Unwrap UVs",
        description = "Will automatically unwrap UVs. If disabled it will only create seams",
    )
    new_uv_map: bpy.props.BoolProperty(
        default = True,
        name = "Create New UVMap",
        description = "Creates new UV Map. If disabled will overwrite active UV Map, if it exists",
    )
    keep_existing_seams: bpy.props.BoolProperty(
        default = False,
        name = "Keep Existing Seams",
        description = "Keep existing seams and use them for UV unwrapping alongside face set boundaries",
    )

    @classmethod
    def poll(cls, context):
        return context.object and context.object.mode == 'SCULPT'

    def execute(self,context):
        # Create Attributes
        mesh = context.sculpt_object.data
        attribute, values = create_copy_atribute(mesh, "face_sets")

        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(mesh)

        # Clear Existing Seams
        if not self.keep_existing_seams:
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.mark_seam(clear=True)
        bpy.ops.mesh.select_all(action='DESELECT')

        # select_face_sets
        for target in range(max(values) + 1):
            for face, value in zip(bm.faces, values):
                if value == target:
                    face.select = True

            # Mark Face Set Boundaries as Seams
            boundary_edges = get_boundary_edges(bm)
            for edge in boundary_edges:
                edge.seam = True

            # deselect_again
            bpy.ops.mesh.select_all(action='DESELECT')

        # Unwrap
        if self.unwrap:
            bpy.ops.mesh.select_all(action='SELECT')
            if self.new_uv_map:
                uv = mesh.uv_layers.new(name="FaceSetUV")
                uv.active = True
            bpy.ops.uv.unwrap()

        bmesh.update_edit_mesh(mesh)
        bpy.ops.object.mode_set(mode='SCULPT')

        self.report({'INFO'}, "UVMap created from face set boundaries")
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


#class SCULPT_OT_face_sets_to_color_attribute(bpy.types.Operator):
#    bl_idname = "sculpt.face_sets_to_color_attribute"
#    bl_label = "Face Sets to Color Attribute"
#    bl_description = "Convert the Face Set selections to color attribute"
#    bl_options = {'REGISTER','UNDO'}

#    def execute(self, context):
#        obj = context.sculpt_object
#        mesh = obj.data

#        # Create attributes '.sculpt_face_set'
#        if ".sculpt_face_set" not in mesh.attributes:
#            mesh.attributes.new(".sculpt_face_set", "INT", "FACE")
#        attr_faceset = mesh.attributes['.sculpt_face_set'].data
#        
#        faceset_index_dict = dict()
#        for i, faceset_data_value in enumerate(list(set(map(lambda data: data.value, attr_faceset)))):
#            faceset_index_dict[faceset_data_value] = i
#        max_index = len(faceset_index_dict)
#            
#        # Create "Face Sets Col" color attribute
#        if 'Face Sets Col' in mesh.color_attributes:
#            mesh.color_attributes.remove(mesh.color_attributes['Face Sets Col'])
#        color_attr = mesh.color_attributes.new(name='Face Sets Col', domain='CORNER', type='BYTE_COLOR')
#        
#        for i, faceset_data in range(max_index):
#            color_attr.data[i].color = faceset_index_dict[faceset_data.value]
#        return {'FINISHED'}



#### ------------------------------ MENUS ------------------------------ ####

def face_set_operators_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator('sculpt.face_sets_to_materials')
    layout.operator('sculpt.face_sets_to_vertex_groups')
    layout.operator('sculpt.face_sets_to_attribute')
    layout.operator('sculpt.face_sets_to_uv')
    #    layout.operator('sculpt.face_sets_to_color_attribute')



#### ------------------------------ REGISTRATION ------------------------------ ####

classes = [
    SCULPT_OT_face_sets_to_materials,
    SCULPT_OT_face_sets_to_vertex_groups,
    SCULPT_OT_face_sets_to_attribute,
    SCULPT_OT_face_sets_to_uv,
#    SCULPT_OT_face_sets_to_color_attribute,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # MENU
    bpy.types.VIEW3D_MT_face_sets.append(face_set_operators_menu)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    # MENU
    bpy.types.VIEW3D_MT_face_sets.remove(face_set_operators_menu)
