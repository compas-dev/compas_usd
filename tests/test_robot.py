import os
import pytest

from pxr import UsdGeom

from compas_robots import RobotModel

from compas_usd.conversions import stage_from_robot


BASE_FOLDER = os.path.dirname(__file__)
FIXTURES_FOLDER = os.path.join(BASE_FOLDER, "fixtures")


@pytest.fixture
def ur5_robot():
    robot = RobotModel.ur5(load_geometry=True)
    return robot


def test_robot_static(ur5_robot):
    """Test static robot export without animation."""
    file_path = os.path.join(FIXTURES_FOLDER, "robot_static.usda")
    stage = stage_from_robot(ur5_robot, file_path)

    # Check stage was created
    assert stage is not None

    # Check root prim exists
    root_prim = stage.GetPrimAtPath("/ur5")
    assert root_prim.IsValid()

    # Check visual prims exist for links with geometry
    for link in ur5_robot.iter_links():
        if link.visual:
            visual_path = f"/ur5/{link.name}_visual_0_0"
            visual_prim = stage.GetPrimAtPath(visual_path)
            assert visual_prim.IsValid(), f"Visual prim {visual_path} should exist"


def test_robot_animated(ur5_robot):
    """Test animated robot export with trajectory."""
    file_path = os.path.join(FIXTURES_FOLDER, "robot_animated.usda")

    # Create 2-second trajectory at 24fps = 48 frames
    fps = 24.0
    duration = 2.0
    num_frames = int(fps * duration)

    trajectory = []
    for i in range(num_frames + 1):
        t = i / num_frames  # 0 to 1
        config = ur5_robot.zero_configuration()
        # Animate shoulder_pan from 0 to 2 radians
        config["shoulder_pan_joint"] = 2.0 * t
        # Animate shoulder_lift from 0 to -0.5 and back
        config["shoulder_lift_joint"] = -0.5 * (1 - abs(2 * t - 1))
        # Animate elbow from 0 to 1 radian
        config["elbow_joint"] = 1.0 * t
        trajectory.append(config)

    stage = stage_from_robot(ur5_robot, file_path, trajectory=trajectory, fps=fps)

    # Check timeline is set (2 seconds at 24fps)
    assert stage.GetStartTimeCode() == 0
    assert stage.GetEndTimeCode() == num_frames
    assert stage.GetTimeCodesPerSecond() == fps

    # Check that transforms are time-sampled on visual prims
    shoulder_visual_prim = stage.GetPrimAtPath("/ur5/shoulder_link_visual_0_0")
    assert shoulder_visual_prim.IsValid()

    xformable = UsdGeom.Xformable(shoulder_visual_prim)
    xform_ops = xformable.GetOrderedXformOps()
    assert len(xform_ops) > 0, "Should have xform ops"

    # Check time samples exist
    xform_op = xform_ops[0]
    time_samples = xform_op.GetTimeSamples()
    assert len(time_samples) == num_frames + 1, f"Should have {num_frames + 1} time samples, got {len(time_samples)}"
