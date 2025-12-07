"""
********************************************************************************
compas_usd.conversions
********************************************************************************

.. currentmodule:: compas_usd.conversions

.. toctree::
    :maxdepth: 2
"""
from __future__ import absolute_import

from .geometry import prim_from_box, box_from_prim, prim_from_cylinder, prim_from_sphere, prim_from_mesh, prim_from_transformation, prim_default
from .transformations import (
    gfmatrix4d_from_transformation,
    transformation_from_gfmatrix4d,
    gfvec3f_and_gfquatd_from_frame,
    xform_rotate_from_frame,
    apply_transformation_on_prim,
    apply_rotate_and_translate_on_prim,
    frame_and_scale_from_prim,
)
from .scene import stage_from_scene
from .robot import stage_from_robot, prim_from_link

__all__ = [
    "prim_from_box",
    "box_from_prim",
    "prim_from_cylinder",
    "prim_from_sphere",
    "prim_from_mesh",
    "prim_from_transformation",
    "prim_default",
    "gfmatrix4d_from_transformation",
    "transformation_from_gfmatrix4d",
    "gfvec3f_and_gfquatd_from_frame",
    "xform_rotate_from_frame",
    "apply_transformation_on_prim",
    "apply_rotate_and_translate_on_prim",
    "frame_and_scale_from_prim",
    "stage_from_scene",
    "stage_from_robot",
    "prim_from_link",
]
