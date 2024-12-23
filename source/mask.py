import bpy


#### ------------------------------ OPERATORS ------------------------------ ####
    
class MESH_OT_selection_to_mask(bpy.types.Operator):
    """Create sculpt mode mask from selected vertices in edit mode"""
    bl_idname = "mesh.selection_to_mask"
    bl_label = "Selection to Sculpt Mask"
    bl_description = ("Mask selected vertices in sculpt mode.\n"
                      "WARNING: Will unhide hidden vertices")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.mode in ('EDIT', 'SCULPT')

    def execute(self, context):
        mesh = context.object.data
        bpy.ops.object.mode_set(mode='EDIT')

        # store_hidden_vertices
        # hidden_verts = []
        # for vert in mesh.vertices:
        #     if vert.hide == True:
        #         hidden_verts.append(vert)

        # Hide Unselected
        bpy.ops.mesh.hide(unselected=True)

        # Mask Flood Fill
        bpy.ops.object.mode_set(mode='SCULPT')
        bpy.ops.paint.mask_flood_fill(mode='VALUE', value=1)

        # restore_mesh
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.reveal()
        bpy.ops.mesh.select_all(action='DESELECT')

        bpy.ops.object.mode_set(mode='SCULPT')
        return {'FINISHED'}
    


#### ------------------------------ MENUS ------------------------------ ####

def edit_mode_mask_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator('mesh.selection_to_mask')


def mask_operators_menu(self, context):
    layout = self.layout
    layout.operator('mesh.selection_to_mask', text='Mask from Edit Mode Selection')



#### ------------------------------ REGISTRATION ------------------------------ ####

classes = [
    MESH_OT_selection_to_mask,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # MENUS
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(edit_mode_mask_menu)
    bpy.types.VIEW3D_MT_mask.append(mask_operators_menu)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # MENUS
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(edit_mode_mask_menu)
    bpy.types.VIEW3D_MT_mask.remove(mask_operators_menu)
