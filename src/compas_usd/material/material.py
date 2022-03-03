import os

from pxr import Sdf
from pxr import UsdShade
from pxr import UsdGeom

class USDMaterial(object):
    """Wrapper about UsdShade.Material
    """
    def __init__(self, stage, name, materials_path='/Looks'):
        self.stage = stage

        if not stage.GetPrimAtPath(materials_path):
            prim = UsdGeom.Scope.Define(stage, materials_path)
            print(prim)

        
        material_path = Sdf.Path(materials_path).AppendChild(name)
        self.material = UsdShade.Material.Define(stage, material_path)
        self.surface_output = self.material.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        self.displacement_output = self.material.CreateOutput("displacement", Sdf.ValueTypeNames.Token)

    def GetPath(self):
        return self.material.GetPath()

    @classmethod
    def from_material(cls, stage, material):
        """Create a material from a compas_xr.material
        """
        umat = cls(stage, material.name)

        ps = USDPreviewSurface(stage, umat, "shader")
        ps.initialize_from_material(material)
        return umat
    
    @classmethod
    def from_mdl(cls, stage, filepath, material_name=None):
        """Create a material from a MDL file
        """
        # get the relative path between stage and mdl
        material_name = material_name or os.path.splitext(os.path.basename(filepath))[0]
        stage_path = stage.GetRootLayer().realPath
        mdl_relative_path = os.path.relpath(filepath, stage_path)

        umat = cls(stage, material_name)

        material_path = umat.GetPath()

        mdlShader = UsdShade.Shader.Define(stage, material_path.AppendChild("Shader"))
        mdlShader.CreateIdAttr("mdlMaterial")
        mdlShaderModule = mdl_relative_path.replace("\\","/") # TODO ?
        mdlShaderModule = "./" + mdlShaderModule

        mdlShader.SetSourceAsset(mdlShaderModule, "mdl")
        mdlShader.GetPrim().CreateAttribute("info:mdl:sourceAsset:subIdentifier", Sdf.ValueTypeNames.Token, True).Set(material_name)
        umat.material.CreateSurfaceOutput().ConnectToSource(mdlShader.ConnectableAPI(), "out")
        # later: UsdShade.MaterialBindingAPI(prim).Bind(material)
        return umat


class USDPreviewSurface(object):
    """Material that models a physically based surface for USD.
    """

    def __init__(self, stage, material, scale_texture=False):
        self.stage = stage
        self.scale_texture = scale_texture
        self.material = material
        # self.output_directory = output_directory # for images
        self.shader = UsdShade.Shader.Define(stage, material.GetPath().AppendChild("Shader")) # why not already defined in material.. multiple shader possible?
        self.shader.CreateIdAttr('UsdPreviewSurface')
        self._initialize_material()

    def _initialize_material(self):
        shader = self.shader
        self._use_specular_workflow = shader.CreateInput('useSpecularWorkflow', Sdf.ValueTypeNames.Int)
        self._use_specular_workflow.Set(False)

        surface_output = shader.CreateOutput('surface', Sdf.ValueTypeNames.Token)
        self.material.surface_output.ConnectToSource(surface_output)

        displacement_output = shader.CreateOutput('displacement', Sdf.ValueTypeNames.Token)
        self.material.displacement_output.ConnectToSource(displacement_output)

        self._specular_color = shader.CreateInput('specularColor', Sdf.ValueTypeNames.Color3f)
        self._specular_color.Set((0.0, 0.0, 0.0))
        self._metallic = shader.CreateInput('metallic', Sdf.ValueTypeNames.Float)
        self._roughness = shader.CreateInput('roughness', Sdf.ValueTypeNames.Float)
        self._clearcoat = shader.CreateInput('clearcoat', Sdf.ValueTypeNames.Float)
        self._clearcoat.Set(0.0)
        self._clearcoat_roughness = shader.CreateInput('clearcoatRoughness', Sdf.ValueTypeNames.Float)
        self._clearcoat_roughness.Set(0.01)
        self._opacity = shader.CreateInput('opacity', Sdf.ValueTypeNames.Float)
        self._ior = shader.CreateInput('ior', Sdf.ValueTypeNames.Float)
        self._ior.Set(1.5)
        self._normal = shader.CreateInput('normal', Sdf.ValueTypeNames.Normal3f)
        self._displacement = shader.CreateInput('displacement', Sdf.ValueTypeNames.Float)
        self._displacement.Set(0.0)
        self._occlusion = shader.CreateInput('occlusion', Sdf.ValueTypeNames.Float)
        self._emissive_color = shader.CreateInput('emissiveColor', Sdf.ValueTypeNames.Color3f)
        self._diffuse_color = shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f)

        # self._st0 = USDPrimvarReaderFloat2(self._stage, self._usd_material._material_path, 'st0')
        # self._st1 = USDPrimvarReaderFloat2(self._stage, self._usd_material._material_path, 'st1')





if __name__ == "__main__":
    from pxr import Usd
    from compas_usd import DATA

    stage = Usd.Stage.CreateNew(os.path.join(DATA, "materials.usda"))
    ## https://graphics.pixar.com/usd/release/api/class_usd_stage.html

    #stage = Usd.Stage.CreateInMemory()

    USDMaterial.from_mdl(stage, os.path.join(DATA, "materials", "grey.mdl"))
    USDMaterial.from_mdl(stage, os.path.join(DATA, "materials", "blue.mdl"))

    material = USDMaterial(stage, "preview_surface")
    preview_surface = USDPreviewSurface(stage, material)

    print(stage.GetRootLayer().ExportToString())

    stage.GetRootLayer().Save()