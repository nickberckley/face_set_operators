bl_info = {
    "name": "Face Set Operators",
    "author": "Nika Kutsniashvili (nickberckley), Gakgu",
    "version": (1, 0),
    "blender": (3, 4, 0),
    "location": "Sculpt Mode > Face Sets",
    "description": "Create material slots, vertex groups, seams, uv islands, and named attributes from sculpt Face Sets",
    "category": "Sculpt",
}

import bpy
from . import(
    face_sets,
    mask,
)


#### ------------------------------ REGISTRATION ------------------------------ ####

modules = [
    face_sets,
    mask,
]
    
def register():
    for module in modules:
        module.register()

def unregister():
    for module in reversed(modules):
        module.unregister()

if __name__ == "__main__":
    register()
