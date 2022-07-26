from pxr import UsdGeom
from compas.geometry import Frame
from compas.utilities import flatten
from .transformations import apply_rotate_and_translate_on_prim
from .transformations import apply_transformation_on_prim


def prim_from_box(stage, path, box):
    """Returns a `UsdGeom.Cube`

    Examples
    --------
    >>> box = Box(Frame.worldXY(), 1, 1, 1)
    >>> prim_from_box(stage, "/box", box)
    UsdGeom.Cube(Usd.Prim(</box>))
    """

    prim = UsdGeom.Cube.Define(stage, path)
    prim.GetPrim().GetAttribute("size").Set(1.0)
    UsdGeom.XformCommonAPI(prim).SetScale((box.xsize, box.ysize, box.zsize))
    apply_rotate_and_translate_on_prim(prim, box.frame)
    return prim


def prim_from_cylinder(stage, path, cylinder):
    """Returns a `UsdGeom.Cylinder`

    Examples
    --------
    >>>
    """
    prim = UsdGeom.Cylinder.Define(stage, path)
    prim.GetHeightAttr().Set(cylinder.height)
    prim.GetRadiusAttr().Set(cylinder.radius)
    prim.GetAxisAttr().Set("Z")
    # How to specify the refinement level for the render view? The following
    # does not work: UsdImagingDelegate.SetRefineLevel(path, 2)
    apply_rotate_and_translate_on_prim(prim, Frame.from_plane(cylinder.plane))
    return prim


def prim_from_sphere(stage, path, sphere):
    """Returns a ``pxr.UsdGeom.Sphere``

    Examples
    --------
    >>> sphere = Sphere((0, 0, 0), 5)
    >>> prim_from_sphere(stage, "/sphere", sphere)
    UsdGeom.Sphere(Usd.Prim(</sphere>))
    """
    prim = UsdGeom.Sphere.Define(stage, path)
    prim.GetPrim().GetAttribute("radius").Set(sphere.radius)
    UsdGeom.XformCommonAPI(prim).SetTranslate(tuple(sphere.point))
    return prim


def prim_from_mesh(stage, path, mesh):
    """Returns a ``pxr.UsdGeom.Mesh``

    Examples
    --------
    >>> box = Box(Frame.worldXY(), 1, 1, 1)
    >>> mesh = Mesh.from_shape(box)
    >>> prim_from_mesh(stage, "/mesh", mesh)
    UsdGeom.Mesh(Usd.Prim(</mesh>))
    """
    prim = UsdGeom.Mesh.Define(stage, path)
    vertices, faces = mesh.to_vertices_and_faces()
    prim.CreatePointsAttr(vertices)
    prim.CreateFaceVertexCountsAttr([len(f) for f in faces])
    prim.CreateFaceVertexIndicesAttr(list(flatten(faces)))
    return prim


def prim_from_transformation(stage, path, transformation):
    """Returns a ``pxr.UsdGeom.Xform``

    Examples
    --------
    >>> transformation = Transformation()
    >>> prim_from_transformation(stage, "/xform", transformation)
    UsdGeom.Xform(Usd.Prim(</xform>))
    """
    prim = UsdGeom.Xform.Define(stage, path)
    apply_transformation_on_prim(prim, transformation)
    return prim


def prim_default(stage, path, transformation=None):  # TODO: This is almost identical to prim_from_transformation
    """Returns a ``pxr.UsdGeom.Xform``

    Examples
    --------
    >>> transformation = Transformation()
    >>> prim_default(stage, "/xform", transformation)
    UsdGeom.Xform(Usd.Prim(</xform>))
    """
    prim = UsdGeom.Xform.Define(stage, path)
    if transformation:
        apply_transformation_on_prim(prim, transformation)
    return prim
