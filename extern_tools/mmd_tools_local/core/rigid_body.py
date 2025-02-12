# -*- coding: utf-8 -*-
# Copyright 2014 MMD Tools authors
# This file is part of MMD Tools.

import bpy

SHAPE_SPHERE = 0
SHAPE_BOX = 1
SHAPE_CAPSULE = 2

MODE_STATIC = 0
MODE_DYNAMIC = 1
MODE_DYNAMIC_BONE = 2


def shapeType(collision_shape):
    return ("SPHERE", "BOX", "CAPSULE").index(collision_shape)


def collisionShape(shape_type):
    return ("SPHERE", "BOX", "CAPSULE")[shape_type]


def setRigidBodyWorldEnabled(enable):
    if bpy.ops.rigidbody.world_add.poll():
        bpy.ops.rigidbody.world_add()
    rigidbody_world = bpy.context.scene.rigidbody_world
    enabled = rigidbody_world.enabled
    rigidbody_world.enabled = enable
    return enabled


class RigidBodyMaterial:
    COLORS = [
        0x7FDDD4,
        0xF0E68C,
        0xEE82EE,
        0xFFE4E1,
        0x8FEEEE,
        0xADFF2F,
        0xFA8072,
        0x9370DB,
        0x40E0D0,
        0x96514D,
        0x5A964E,
        0xE6BFAB,
        0xD3381C,
        0x165E83,
        0x701682,
        0x828216,
    ]

    @classmethod
    def getMaterial(cls, number):
        number = int(number)
        material_name = "mmd_tools_rigid_%d" % (number)
        if material_name not in bpy.data.materials:
            mat = bpy.data.materials.new(material_name)
            color = cls.COLORS[number]
            mat.diffuse_color[:3] = [((0xFF0000 & color) >> 16) / float(255), ((0x00FF00 & color) >> 8) / float(255), (0x0000FF & color) / float(255)]
            mat.specular_intensity = 0
            if len(mat.diffuse_color) > 3:
                mat.diffuse_color[3] = 0.5
            mat.blend_method = "BLEND"
            mat.shadow_method = "NONE"
            mat.use_backface_culling = True
            mat.show_transparent_back = False
            mat.use_nodes = True
            nodes, links = mat.node_tree.nodes, mat.node_tree.links
            nodes.clear()
            node_color = nodes.new("ShaderNodeBackground")
            node_color.inputs["Color"].default_value = mat.diffuse_color
            node_output = nodes.new("ShaderNodeOutputMaterial")
            links.new(node_color.outputs[0], node_output.inputs["Surface"])
        else:
            mat = bpy.data.materials[material_name]
        return mat
