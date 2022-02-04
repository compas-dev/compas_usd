import math
import os
import time

import pytest
import compas
from pxr import Usd
from compas.datastructures import Mesh
from compas.geometry import Frame
from compas.geometry import Rotation
from compas.geometry import Transformation
from compas.geometry import Scale
from compas.geometry import allclose
from compas.geometry import Box
from compas.geometry import Sphere


@pytest.fixture(autouse=True)
def add_imports(doctest_namespace):
    doctest_namespace["os"] = os
    doctest_namespace["math"] = math
    doctest_namespace["time"] = time
    doctest_namespace["Mesh"] = Mesh
    doctest_namespace["Frame"] = Frame
    doctest_namespace["Scale"] = Scale
    doctest_namespace["compas"] = compas
    doctest_namespace["allclose"] = allclose
    doctest_namespace["Rotation"] = Rotation
    doctest_namespace["Transformation"] = Transformation
    doctest_namespace["Box"] = Box
    doctest_namespace["Sphere"] = Sphere
    doctest_namespace["Frame"] = Frame

    stage = Usd.Stage.CreateInMemory()
    doctest_namespace["stage"] = stage
