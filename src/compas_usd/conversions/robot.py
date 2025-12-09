from compas_robots import RobotModel
from compas_robots.model import Link
from compas.geometry import Transformation

from pxr import Sdf, Usd, UsdGeom

from .geometry import prim_from_mesh
from .transformations import gfmatrix4d_from_transformation, apply_transformation_on_prim


def stage_from_robot(robot: RobotModel, file_path: str, trajectory: list = None, fps: float = 24.0) -> Usd.Stage:
    """Converts a :class:`compas_robots.RobotModel` to a USD stage.

    Parameters
    ----------
    robot : :class:`compas_robots.RobotModel`
        The robot model to convert.
    file_path : str
        The file path to save the USD stage.
    trajectory : list[:class:`compas_robots.Configuration`], optional
        List of configurations for animation. If None, exports static zero-config pose.
    fps : float, optional
        Frames per second for animation. Default is 24.0.

    Returns
    -------
    :class:`pxr.Usd.Stage`
        The USD stage.
    """
    stage = Usd.Stage.CreateNew(file_path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

    if trajectory:
        stage.SetStartTimeCode(0)
        stage.SetEndTimeCode(len(trajectory) - 1)
        stage.SetTimeCodesPerSecond(fps)

    root_path = Sdf.Path.absoluteRootPath.AppendChild(robot.name.replace(" ", "_"))
    UsdGeom.Xform.Define(stage, root_path)

    # Create visual prims for each link
    # Each visual gets its own Xform that will be animated
    visual_prims = {}
    for link in robot.iter_links():
        for i, visual in enumerate(link.visual):
            shape = visual.geometry.shape
            if hasattr(shape, "meshes") and shape.meshes:
                for j, mesh in enumerate(shape.meshes):
                    visual_name = f"{link.name}_visual_{i}_{j}".replace(" ", "_")
                    visual_path = root_path.AppendChild(visual_name)
                    xform = UsdGeom.Xform.Define(stage, visual_path)
                    mesh_path = visual_path.AppendChild("mesh")
                    prim_from_mesh(stage, mesh_path, mesh)

                    # Store visual prim with its link and visual reference
                    if link.name not in visual_prims:
                        visual_prims[link.name] = []
                    visual_prims[link.name].append((xform, visual))

    if trajectory:
        apply_animation(stage, robot, visual_prims, trajectory)
    else:
        # Apply static zero-config transforms
        apply_static_transforms(robot, visual_prims)

    stage.Save()
    return stage


def apply_static_transforms(robot: RobotModel, visual_prims: dict):
    """Applies static transforms for zero configuration.

    Parameters
    ----------
    robot : :class:`compas_robots.RobotModel`
        The robot model.
    visual_prims : dict
        Dictionary mapping link names to list of (xform, visual) tuples.
    """
    for link in robot.iter_links():
        if link.name in visual_prims:
            for xform, visual in visual_prims[link.name]:
                # init_transformation contains the world-space transform at zero config
                transform = visual.init_transformation
                if transform:
                    apply_transformation_on_prim(xform, transform)


def prim_from_link(stage: Usd.Stage, path: Sdf.Path, link: Link) -> UsdGeom.Xform:
    """Creates a USD Xform prim for a robot link with its visual geometry.

    Parameters
    ----------
    stage : :class:`pxr.Usd.Stage`
        The USD stage.
    path : :class:`pxr.Sdf.Path`
        The path for the link prim.
    link : :class:`compas_robots.model.Link`
        The robot link.

    Returns
    -------
    :class:`pxr.UsdGeom.Xform`
        The USD Xform prim for the link.
    """
    xform = UsdGeom.Xform.Define(stage, path)

    for i, visual in enumerate(link.visual):
        shape = visual.geometry.shape
        if hasattr(shape, "meshes") and shape.meshes:
            for j, mesh in enumerate(shape.meshes):
                mesh_path = path.AppendChild(f"visual_{i}_{j}")
                prim_from_mesh(stage, mesh_path, mesh)

    return xform


def apply_animation(stage: Usd.Stage, robot: RobotModel, visual_prims: dict, trajectory: list):
    """Applies time-sampled animation to visual transforms.

    Parameters
    ----------
    stage : :class:`pxr.Usd.Stage`
        The USD stage.
    robot : :class:`compas_robots.RobotModel`
        The robot model.
    visual_prims : dict
        Dictionary mapping link names to list of (xform, visual) tuples.
    trajectory : list[:class:`compas_robots.Configuration`]
        List of configurations for each frame.
    """
    # Set up xform ops for each visual
    xform_ops = {}
    for link_name, visuals in visual_prims.items():
        xform_ops[link_name] = []
        for xform, visual in visuals:
            xformable = UsdGeom.Xformable(xform)
            xformable.ClearXformOpOrder()
            xform_ops[link_name].append((xformable.AddTransformOp(), visual))

    for frame_idx, config in enumerate(trajectory):
        time_code = Usd.TimeCode(frame_idx)
        transformations = robot.compute_transformations(config)

        for link in robot.iter_links():
            if link.name not in xform_ops:
                continue

            # Get joint transform for this link
            if link.parent_joint and link.parent_joint.name in transformations:
                joint_transform = transformations[link.parent_joint.name]
            else:
                joint_transform = Transformation()

            # Apply joint transform to each visual's init_transformation
            for xform_op, visual in xform_ops[link.name]:
                if visual.init_transformation:
                    # Compose: joint_transform * init_transformation
                    world_transform = joint_transform * visual.init_transformation
                else:
                    world_transform = joint_transform

                matrix = gfmatrix4d_from_transformation(world_transform)
                xform_op.Set(matrix, time_code)
