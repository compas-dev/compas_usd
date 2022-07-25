import os
import pytest

from compas_usd.material import USDMaterial
from compas_usd.material import USDPreviewSurface

BASE_FOLDER = os.path.dirname(__file__)


@pytest.fixture
def blue_mdl():
    return os.path.join(BASE_FOLDER, "fixtures", "blue.mdl")


@pytest.fixture
def grey_mdl():
    return os.path.join(BASE_FOLDER, "fixtures", "grey.mdl")


def test_blue_material(blue_mdl):

    from pxr import Usd
    from compas_usd import DATA

    # stage = Usd.Stage.CreateNew(os.path.join(DATA, "materials.usda"))
    stage = Usd.Stage.CreateInMemory()
    USDMaterial.from_mdl(stage, blue_mdl)

    material = USDMaterial(stage, "preview_surface")
    preview_surface = USDPreviewSurface(stage, material)

    print(stage.GetRootLayer().ExportToString())
