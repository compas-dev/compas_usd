"""
https://github.com/ColinKennedy/USD-Cookbook/blob/master/concepts/mesh_with_materials/python/material.py
"""
import os

from pxr import Kind, Sdf, Usd, UsdGeom, UsdShade

from compas.datastructures import Mesh
from compas_xr.datastructures import PBRMetallicRoughness
from compas_xr.datastructures import Scene, Material
from compas_xr.datastructures.material import PBRSpecularGlossiness

from compas_xr.conversions.usd import USDScene

BASE_FOLDER = os.path.dirname(__file__)


def attach_billboard(stage, root, name="card"):
    billboard = UsdGeom.Mesh.Define(stage, str(root.GetPath()) + "/" + name)
    billboard.CreatePointsAttr([(-430, -145, 0), (430, -145, 0), (430, 145, 0), (-430, 145, 0)])
    billboard.CreateFaceVertexCountsAttr([4])
    billboard.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    billboard.CreateExtentAttr([(-430, -145, 0), (430, 145, 0)])
    texCoords = billboard.CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
    texCoords.Set([(0, 0), (1, 0), (1, 1), (0, 1)])
    return billboard


def compas_attach_billboard(scene, root, name="card", mkey=0):
    vertices = [(-430, -145, 0), (430, -145, 0), (430, 145, 0), (-430, 145, 0)]
    faces = [[0, 1, 2, 3]]
    billboard = Mesh.from_vertices_and_faces(vertices, faces)
    texture_coordinates = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for k, v in zip(billboard.vertices(), texture_coordinates):
        billboard.vertex_attribute(k, "texture_coordinate", value=v)
    print(">>", billboard.vertices_attribute("texture_coordinate"))
    scene.add_layer(name, parent=root, element=billboard, material=mkey)


def attach_surface_shader(stage, material, path):
    shader = UsdShade.Shader.Define(stage, path)
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return shader


def compas_attach_surface_shader(material):
    material.pbr_metallic_roughness = PBRMetallicRoughness()
    material.pbr_metallic_roughness.metallic_factor = 0.0
    material.pbr_metallic_roughness.roughness_factor = 0.4
    # material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")


def attach_texture(stage, shader, material_path, reader_name="stReader", shader_name="diffuseTexture"):
    reader = UsdShade.Shader.Define(stage, material_path + "/" + reader_name)
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    diffuseTextureSampler = UsdShade.Shader.Define(stage, material_path + "/" + shader_name)
    diffuseTextureSampler.CreateIdAttr("UsdUVTexture")
    diffuseTextureSampler.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(os.path.join(BASE_FOLDER, "fixtures", "USDLogoLrg.png"))
    diffuseTextureSampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(), "result")
    diffuseTextureSampler.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(diffuseTextureSampler.ConnectableAPI(), "rgb")
    return reader


def compas_attach_texture(scene, material):

    from compas_xr.datastructures.material import MineType
    from compas_xr.datastructures.material import Texture
    from compas_xr.datastructures.material import TextureInfo
    from compas_xr.datastructures.material import Image

    image_uri = "USDLogoLrg.png"
    image_file = os.path.join(BASE_FOLDER, "fixtures", image_uri)
    image_data = Image(name=image_uri, mime_type=MineType.PNG, uri=image_file)
    image_idx = scene.add_image(image_data)

    texture = Texture(source=image_idx, name="UsdUVTexture")
    texture_idx = scene.add_texture(texture)
    material.pbr_specular_glossiness = PBRSpecularGlossiness()
    material.pbr_specular_glossiness.diffuse_texture = TextureInfo(index=texture_idx)

    # diffuseTextureSampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(), "result")
    # diffuseTextureSampler.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    # shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(diffuseTextureSampler.ConnectableAPI(), "rgb")
    # return reader


def main():
    """Run the main execution of the current script."""
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    root = UsdGeom.Xform.Define(stage, "/TexModel")
    Usd.ModelAPI(root).SetKind(Kind.Tokens.component)

    UsdGeom.Scope.Define(stage, "/Looks")

    billboard = attach_billboard(stage, root)
    # material = UsdShade.Material.Define(stage, str(billboard.GetPath()) + "/" + "boardMat")
    material = UsdShade.Material.Define(stage, "/Looks/" + "boardMat")
    shader = attach_surface_shader(stage, material, str(material.GetPath()) + "/" + "PBRShader")
    reader = attach_texture(stage, shader, str(material.GetPath()))

    st_input = material.CreateInput("frame:stPrimvarName", Sdf.ValueTypeNames.Token)
    st_input.Set("st")

    reader.CreateInput("varname", Sdf.ValueTypeNames.Token).ConnectToSource(st_input)

    UsdShade.MaterialBindingAPI(billboard).Bind(material)

    # print(stage.GetRootLayer().ExportToString())
    filename = os.path.join(BASE_FOLDER, "fixtures", "test1.usda")
    print(filename)
    stage.Export(filename)


def compas_main():

    scene = Scene(up_axis="Y")

    root = scene.add_layer("TexModel")
    # Usd.ModelAPI(root).SetKind(Kind.Tokens.component)

    material = Material(name="boardMat")
    mkey = scene.add_material(material)

    compas_attach_billboard(scene, root, name="card", mkey=mkey)
    compas_attach_surface_shader(material)
    compas_attach_texture(scene, material)

    # UsdShade.MaterialBindingAPI(billboard).Bind(material)

    # print(stage.GetRootLayer().ExportToString())
    # filename = os.path.join(BASE_FOLDER, "fixtures", "test.usda")
    # stage.Export(filename)

    filename = os.path.join(BASE_FOLDER, "fixtures", "test2.usda")
    USDScene.from_scene(scene).to_usd(filename)
    print(filename)


if __name__ == "__main__":
    main()
    compas_main()
