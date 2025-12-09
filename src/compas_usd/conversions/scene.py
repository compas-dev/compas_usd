from compas.scene import Scene
from compas.scene import SceneObject
from compas.data import Data
from compas.geometry import Box
from compas.geometry import Sphere
from compas.geometry import Transformation
from compas.datastructures import Mesh
from compas_usd.conversions import prim_from_transformation
from compas_usd.conversions import prim_from_box
from compas_usd.conversions import prim_from_sphere
from compas_usd.conversions import prim_from_mesh

from pxr import Sdf, Usd, UsdGeom


def stage_from_scene(scene: Scene, file_path: str) -> Usd.Stage:
    """
    Converts a :class:`compas.scene.Scene` to a USD stage.

    Parameters
    ----------
    scene : :class:`compas.scene.Scene`
        The scene to convert.
    file_path : str
        The file path to the USD stage.

    Returns
    -------
    :class:`pxr.Usd.Stage`
        The USD stage.
    """
    stage = Usd.Stage.CreateNew(file_path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    root_path = Sdf.Path.absoluteRootPath.AppendChild(scene.name)
    for obj in scene.root.children:
        prim_from_sceneobject(stage, obj, parent_path=root_path)

    stage.Save()
    return stage


def prim_from_sceneobject(stage: Usd.Stage, sceneobject: SceneObject, parent_path: Sdf.Path = None) -> Usd.Prim:
    """
    Converts a :class:`compas.scene.SceneObject` to a USD prim.

    Parameters
    ----------
    stage : :class:`pxr.Usd.Stage`
        The USD stage.
    sceneobject : :class:`compas.scene.SceneObject`
        The scene object to convert.
    parent_path : :class:`pxr.Sdf.Path`, optional
        The path to the parent prim.

    Returns
    -------
    :class:`pxr.Usd.Prim`
        The USD prim.
    """
    if parent_path is None:
        parent_path = Sdf.Path.absoluteRootPath
    path = parent_path.AppendChild(sceneobject.name)

    transformation = sceneobject.transformation
    if transformation is None:
        transformation = Transformation()
    if sceneobject.item is not None:
        prim_from_item(stage, sceneobject.item, parent_path=path)

    for child in sceneobject.children:
        prim_from_sceneobject(stage, child, parent_path=path)

    return prim


def prim_from_item(stage: Usd.Stage, item: Data, parent_path: Sdf.Path = None) -> Usd.Prim:
    """
    Converts a :class:`compas.scene.SceneObject` to a USD prim.

    Parameters
    ----------
    stage : :class:`pxr.Usd.Stage`
        The USD stage.
    item : :class:`compas.scene.SceneObject`
        The item to convert.
    parent_path : :class:`pxr.Sdf.Path`, optional
        The path to the parent prim.

    Returns
    -------
    :class:`pxr.Usd.Prim`
        The USD prim.
    """
    if parent_path is None:
        parent_path = Sdf.Path.absoluteRootPath
    path = parent_path.AppendChild(item.name)

    if isinstance(item, Box):
        prim = prim_from_box(stage, path, item)
    elif isinstance(item, Sphere):
        prim = prim_from_sphere(stage, path, item)
    elif isinstance(item, Mesh):
        prim = prim_from_mesh(stage, path, item)
    return prim
