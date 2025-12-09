from pxr import UsdGeom
from compas.geometry import Frame
from compas.geometry import Box
from compas.itertools import flatten
from compas.geometry import transpose_matrix

from .transformations import apply_rotate_and_translate_on_prim
from .transformations import apply_transformation_on_prim
from .transformations import frame_and_scale_from_prim


def unflatten(array, n):
    if len(array) % n:
        raise ValueError("The length of the array must be a factor of n: %d %% %d == 0" % (len(array), n))
    return [array[i : (i + n)] for i in range(0, len(array), n)]  # noqa E203


def prim_from_box(stage, path, box):
    """Returns a :class:`UsdGeom.Cube`

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


def box_from_prim(prim):
    """Returns a :class:`compas.geometry.Box`

    Examples
    --------
    >>> box = Box(Frame.worldXY(), 1, 1, 1)
    >>> prim = prim_from_box(stage, "/box", box)
    >>> box_from_prim(prim)
    Box(Frame(Point(0.000, 0.000, 0.000), Vector(1.000, -0.000, 0.000), Vector(0.000, 1.000, -0.000)), 1.0, 1.0, 1.0)
    """
    size = prim.GetPrim().GetAttribute("size").Get()
    frame, scale = frame_and_scale_from_prim(prim)
    xsize, ysize, zsize = scale
    return Box(frame, xsize * size, ysize * size, zsize * size)


def prim_from_cylinder(stage, path, cylinder):
    """Returns a :class:`UsdGeom.Cylinder`

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
    UsdGeom.XformCommonAPI(prim).SetTranslate(tuple(sphere.frame.point))
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


if __name__ == "__main__":
    from pxr import Usd

    stage = Usd.Stage.CreateInMemory()
    box = Box(Frame.worldXY(), 1, 1, 1)
    prim = prim_from_box(stage, "/box", box)
    print(box_from_prim(prim))


def prim_from_surface(stage, path, surface):
    """Returns a ``pxr.UsdGeom.NurbsPatch``

    control_points = [[[0, 0, 0], [0, 4, 0], [0, 8, -3]], [[2, 0, 6], [2, 4, 0], [2, 8, 0]], [[4, 0, 0], [4, 4, 0], [4, 8, 3]], [[6, 0, 0], [6, 4, -3], [6, 8, 0]]]
    degree = (3, 2)
    surface = Surface(control_points, degree)
    prim_from_surface(stage, "/surface", surface)
    UsdGeom.NurbsPatch(Usd.Prim(</surface>))
    """
    degree_u, degree_v = surface.degree
    knot_vector_u, knot_vector_v = surface.knot_vector
    count_u, count_v = surface.count

    # upside down
    weights = list(flatten(surface.weights))
    weights = list(flatten(transpose_matrix(unflatten(weights, count_v))))
    points = list(flatten(surface.control_points))
    points = list(flatten(transpose_matrix(unflatten(points, count_v))))

    prim = UsdGeom.NurbsPatch.Define(stage, path)
    prim.CreateUVertexCountAttr(count_u)
    prim.CreateVVertexCountAttr(count_v)
    prim.CreateUOrderAttr(degree_u + 1)
    prim.CreateVOrderAttr(degree_v + 1)
    prim.CreateUKnotsAttr(knot_vector_u)
    prim.CreateVKnotsAttr(knot_vector_v)
    prim.CreatePointWeightsAttr(weights)
    prim.CreatePointsAttr(points)
    return prim
