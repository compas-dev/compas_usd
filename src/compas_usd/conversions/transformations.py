import math
from pxr import Gf
from pxr import UsdGeom

from compas.geometry import Frame
from compas.geometry import Rotation
from compas.geometry import Transformation
from compas.geometry import transpose_matrix


def gfmatrix4d_from_transformation(transformation):
    """Converts a :class:`compas.geometry.Transformation` to a :class:`Gf.Matrix4d`

    Examples
    --------
    >>> frame = Frame((0, 3, 4), (0.27, 0.95, 0.13), (-0.95, 0.28, -0.09))
    >>> t1 = Transformation.from_frame(frame)
    >>> gf = gfmatrix4d_from_transformation(t1)
    >>> t2 = transformation_from_gfmatrix4d(gf)
    >>> t1 == t2
    True
    """
    return Gf.Matrix4d(*[v for col in transpose_matrix(transformation.matrix) for v in col])


def transformation_from_gfmatrix4d(gfmatrix4d):
    """Converts a :class:`Gf.Matrix4d` to a :class:`compas.geometry.Transformation`

    Examples
    --------
    >>> frame = Frame((0, 3, 4), (0.27, 0.95, 0.13), (-0.95, 0.28, -0.09))
    >>> t1 = Transformation.from_frame(frame)
    >>> gf = gfmatrix4d_from_transformation(t1)
    >>> t2 = transformation_from_gfmatrix4d(gf)
    >>> t1 == t2
    True
    """
    matrix = [[v for v in column] for column in gfmatrix4d]
    return Transformation(transpose_matrix(matrix))


def gfvec3f_and_gfquatd_from_frame(frame):
    w, x, y, z = Rotation.from_frame(frame).quaternion.wxyz
    return Gf.Vec3f(*frame.point), Gf.Quatd(w, x, y, z)


def xform_rotate_from_frame(frame, rotation_order):
    """Returns euler angles for UsdGeom.XformCommonAPI from a :class:`Frame`

    Parameters
    ----------
    frame : :class:`Frame`
        The frame.
    rotation_order : :class:`UsdGeom.XformCommonAPI.RotationOrder`
        The rotation order.

    Returns
    -------
    list[float]
        Euler angles in degrees.
    """
    switcher = {
        UsdGeom.XformCommonAPI.RotationOrderXYZ: "xyz",
        UsdGeom.XformCommonAPI.RotationOrderXZY: "xzy",
        UsdGeom.XformCommonAPI.RotationOrderYXZ: "yxz",
        UsdGeom.XformCommonAPI.RotationOrderYZX: "yzx",
        UsdGeom.XformCommonAPI.RotationOrderZXY: "zxy",
        UsdGeom.XformCommonAPI.RotationOrderZYX: "zyx",
    }

    axes = switcher.get(rotation_order, None)
    return [math.degrees(a) for a in frame.euler_angles(False, axes)]


def frame_and_scale_from_prim(prim):
    translation, rotation, scale, _, rotOrder = UsdGeom.XformCommonAPI(prim).GetXformVectors(0)
    switcher = {
        UsdGeom.XformCommonAPI.RotationOrderXYZ: "xyz",
        UsdGeom.XformCommonAPI.RotationOrderXZY: "xzy",
        UsdGeom.XformCommonAPI.RotationOrderYXZ: "yxz",
        UsdGeom.XformCommonAPI.RotationOrderYZX: "yzx",
        UsdGeom.XformCommonAPI.RotationOrderZXY: "zxy",
        UsdGeom.XformCommonAPI.RotationOrderZYX: "zyx",
    }
    axes = switcher.get(rotOrder, None)
    frame = Frame.from_euler_angles(map(math.radians, rotation), static=False, axes=axes, point=translation)
    return frame, scale


def apply_transformation_on_prim(prim, transformation):
    """ """
    xform = UsdGeom.Xformable(prim)
    transform = xform.AddTransformOp()
    matrix = gfmatrix4d_from_transformation(transformation)
    transform.Set(matrix)


def apply_rotate_and_translate_on_prim(prim, frame):
    _, _, _, _, rotation_order = UsdGeom.XformCommonAPI(prim).GetXformVectors(0)

    euler_angles = xform_rotate_from_frame(frame, rotation_order)

    UsdGeom.XformCommonAPI(prim).SetRotate(euler_angles)
    UsdGeom.XformCommonAPI(prim).SetTranslate(tuple(frame.point))


def translate_and_orient_from_frame(frame):
    w, x, y, z = Rotation.from_frame(frame).quaternion.wxyz
    return Gf.Vec3f(*frame.point), Gf.Quatd(w, x, y, z)
