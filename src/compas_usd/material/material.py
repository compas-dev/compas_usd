import os

from enum import Enum
from pxr import Gf
from pxr import Sdf
from pxr import UsdShade
from pxr import UsdGeom


class AlphaMode(object):  # todo import from somewhere else?
    BLEND = "BLEND"
    MASK = "MASK"
    OPAQUE = "OPAQUE"


class USDMaterial(object):
    """Wrapper about UsdShade.Material"""

    def __init__(self, stage, name, materials_path="/Looks"):
        self.stage = stage

        if not stage.GetPrimAtPath(materials_path):
            UsdGeom.Scope.Define(stage, materials_path)

        material_path = Sdf.Path(materials_path).AppendChild(name)
        self.material = UsdShade.Material.Define(stage, material_path)
        self.surface_output = self.material.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        self.displacement_output = self.material.CreateOutput("displacement", Sdf.ValueTypeNames.Token)

    def GetPath(self):
        return self.material.GetPath()

    @classmethod
    def from_material(cls, stage, material):
        """Create a material from a :class:compas_xr.datastructures.material"""
        umat = cls(stage, material.name)
        USDPreviewSurface.from_material(material, stage, umat)
        return umat

    @classmethod
    def from_mdl(cls, stage, filepath, material_name=None):
        """Create a material from a MDL file"""
        # get the relative path between stage and mdl
        material_name = material_name or os.path.splitext(os.path.basename(filepath))[0]
        stage_path = stage.GetRootLayer().realPath
        mdl_relative_path = os.path.relpath(filepath, stage_path)
        umat = cls(stage, material_name)
        material_path = umat.GetPath()

        mdlShader = UsdShade.Shader.Define(stage, material_path.AppendChild("Shader"))
        mdlShader.CreateIdAttr("mdlMaterial")
        mdlShaderModule = mdl_relative_path.replace("\\", "/")  # TODO ?
        mdlShaderModule = "./" + mdlShaderModule

        mdlShader.SetSourceAsset(mdlShaderModule, "mdl")
        mdlShader.GetPrim().CreateAttribute("info:mdl:sourceAsset:subIdentifier", Sdf.ValueTypeNames.Token, True).Set(material_name)
        umat.material.CreateSurfaceOutput().ConnectToSource(mdlShader.ConnectableAPI(), "out")
        # later: UsdShade.MaterialBindingAPI(prim).Bind(material)
        return umat

    def to_compas(self):
        """Create a :class:`compas_xr.datastructures.Material`"""
        raise NotImplementedError


class USDPreviewSurface(object):
    """Material that models a physically based surface for USD."""

    def __init__(self, stage, material, scale_texture=False):
        self.stage = stage
        self.scale_texture = scale_texture
        self.material = material
        # self.output_directory = output_directory # for images
        self.shader = UsdShade.Shader.Define(stage, material.GetPath().AppendChild("Shader"))  # why not already defined in material.. multiple shader possible?
        self.shader.CreateIdAttr("UsdPreviewSurface")
        self._initialize_material()

    def _initialize_material(self):
        shader = self.shader
        self._use_specular_workflow = shader.CreateInput("useSpecularWorkflow", Sdf.ValueTypeNames.Int)
        self._use_specular_workflow.Set(False)

        surface_output = shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        self.material.surface_output.ConnectToSource(surface_output)

        displacement_output = shader.CreateOutput("displacement", Sdf.ValueTypeNames.Token)
        self.material.displacement_output.ConnectToSource(displacement_output)

        self._specular_color = shader.CreateInput("specularColor", Sdf.ValueTypeNames.Color3f)
        self._specular_color.Set((0.0, 0.0, 0.0))
        self._metallic = shader.CreateInput("metallic", Sdf.ValueTypeNames.Float)
        self._roughness = shader.CreateInput("roughness", Sdf.ValueTypeNames.Float)
        self._clearcoat = shader.CreateInput("clearcoat", Sdf.ValueTypeNames.Float)
        self._clearcoat.Set(0.0)
        self._clearcoat_roughness = shader.CreateInput("clearcoatRoughness", Sdf.ValueTypeNames.Float)
        self._clearcoat_roughness.Set(0.01)
        self._opacity = shader.CreateInput("opacity", Sdf.ValueTypeNames.Float)
        self._ior = shader.CreateInput("ior", Sdf.ValueTypeNames.Float)
        self._ior.Set(1.5)
        self._normal = shader.CreateInput("normal", Sdf.ValueTypeNames.Normal3f)
        self._displacement = shader.CreateInput("displacement", Sdf.ValueTypeNames.Float)
        self._displacement.Set(0.0)
        self._occlusion = shader.CreateInput("occlusion", Sdf.ValueTypeNames.Float)
        self._emissive_color = shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f)
        self._diffuse_color = shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)

        # self._st0 = USDPrimvarReaderFloat2(self._stage, self._usd_material._material_path, 'st0')
        # self._st1 = USDPrimvarReaderFloat2(self._stage, self._usd_material._material_path, 'st1')

    @classmethod
    def from_material(cls, material, stage, usd_material):
        ps = cls(stage, usd_material)
        ps._set_normal_texture(material)
        ps._set_emissive_texture(material)
        ps._set_occlusion_texture(material)
        # self._set_khr_material_pbr_specular_glossiness(gltf_material) # extensions!
        ps._set_pbr_metallic_roughness(material)
        return ps

    def _set_normal_texture(self, material):
        normal_texture = material.normal_texture
        if normal_texture is None:
            self._normal.Set((0, 0, 1))
        else:
            destination = normal_texture.write_to_directory(self.output_directory, GLTFImage.ImageColorChannels.RGB)
            normal_scale = normal_texture.scale
            scale_factor = (normal_scale, normal_scale, normal_scale, 1.0)
            usd_uv_texture = USDUVTexture("normalTexture", self._stage, self._usd_material._usd_material, normal_texture, [self._st0, self._st1])
            usd_uv_texture._file_asset.Set(destination)
            usd_uv_texture._scale.Set(scale_factor)
            usd_uv_texture._fallback.Set(scale_factor)
            texture_shader = usd_uv_texture.get_shader()
            texture_shader.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
            self._normal.ConnectToSource(texture_shader, "rgb")

    def _set_emissive_texture(self, gltf_material):
        emissive_texture = gltf_material.emissive_texture
        emissive_factor = gltf_material.emissive_factor
        if not emissive_texture:
            self._emissive_color.Set((0, 0, 0))
        else:
            destination = emissive_texture.write_to_directory(self._output_directory, GLTFImage.ImageColorChannels.RGB)
            scale_factor = (emissive_factor[0], emissive_factor[1], emissive_factor[2], 1.0)
            usd_uv_texture = USDUVTexture("emissiveTexture", self._stage, self._usd_material._usd_material, emissive_texture, [self._st0, self._st1])
            usd_uv_texture._file_asset.Set(destination)
            usd_uv_texture._scale.Set(scale_factor)
            usd_uv_texture._fallback.Set(scale_factor)
            texture_shader = usd_uv_texture.get_shader()
            texture_shader.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
            self._emissive_color.ConnectToSource(texture_shader, "rgb")

    def _set_occlusion_texture(self, gltf_material):
        occlusion_texture = gltf_material.occlusion_texture
        if not occlusion_texture:
            self._occlusion.Set(1.0)
        else:
            destination = occlusion_texture.write_to_directory(self._output_directory, GLTFImage.ImageColorChannels.R)
            occlusion_strength = occlusion_texture.strength
            strength_factor = (occlusion_strength, occlusion_strength, occlusion_strength, 1.0)
            usd_uv_texture = USDUVTexture("occlusionTexture", self._stage, self._usd_material._usd_material, occlusion_texture, [self._st0, self._st1])
            usd_uv_texture._file_asset.Set(destination)
            usd_uv_texture._scale.Set(strength_factor)
            usd_uv_texture._fallback.Set(strength_factor)
            texture_shader = usd_uv_texture.get_shader()
            texture_shader.CreateOutput("r", Sdf.ValueTypeNames.Float)
            self._occlusion.ConnectToSource(texture_shader, "r")

    def _set_pbr_metallic_roughness(self, gltf_material):
        pbr_metallic_roughness = gltf_material.pbr_metallic_roughness
        if pbr_metallic_roughness:
            self._set_pbr_base_color(pbr_metallic_roughness, gltf_material.alpha_mode)
            self._set_pbr_metallic(pbr_metallic_roughness)
            self._set_pbr_roughness(pbr_metallic_roughness)

    def _set_khr_material_pbr_specular_glossiness(self, gltf_material):
        extensions = gltf_material.extensions
        if "KHR_materials_pbrSpecularGlossiness" not in extensions:
            self._set_pbr_metallic_roughness(gltf_material)
        else:
            self._use_specular_workflow.Set(True)
            pbr_specular_glossiness = extensions["KHR_materials_pbrSpecularGlossiness"]
            self._set_pbr_specular_glossiness_diffuse(pbr_specular_glossiness)
            self._set_pbr_specular_glossiness_glossiness(pbr_specular_glossiness)
            self._set_pbr_specular_glossiness_specular(pbr_specular_glossiness)

    def _set_pbr_specular_glossiness_diffuse(self, pbr_specular_glossiness):
        diffuse_texture = pbr_specular_glossiness.get_diffuse_texture()
        diffuse_factor = pbr_specular_glossiness.get_diffuse_factor()
        if not diffuse_texture:
            self._diffuse_color.Set(Gf.Vec3f(diffuse_factor[0], diffuse_factor[1], diffuse_factor[2]))
        else:
            destination = diffuse_texture.write_to_directory(self._output_directory, GLTFImage.ImageColorChannels.RGB)
            scale_factor = tuple(diffuse_factor)
            usd_uv_texture = USDUVTexture("diffuseTexture", self._stage, self._usd_material._usd_material, diffuse_texture, [self._st0, self._st1])
            usd_uv_texture._file_asset.Set(destination)
            usd_uv_texture._scale.Set(scale_factor)
            usd_uv_texture._fallback.Set(scale_factor)
            texture_shader = usd_uv_texture.get_shader()
            texture_shader.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
            texture_shader.CreateOutput("a", Sdf.ValueTypeNames.Float)
            self._diffuse_color.ConnectToSource(texture_shader, "rgb")
            self._opacity.ConnectToSource(texture_shader, "a")

    def _uv_texture(self, name, specular_glossiness_texture, destination, scale_factor, apply_on, mode):

        usd_uv_texture = USDUVTexture(name, self._stage, self._usd_material._usd_material, specular_glossiness_texture, [self._st0, self._st1])
        usd_uv_texture._file_asset.Set(destination)
        usd_uv_texture._scale.Set(scale_factor)
        usd_uv_texture._fallback.Set(scale_factor)
        texture_shader = usd_uv_texture.get_shader()
        if mode == "rgb":
            texture_shader.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
        elif mode == "r":
            texture_shader.CreateOutput("r", Sdf.ValueTypeNames.Float)
        apply_on.ConnectToSource(texture_shader, mode)
        return texture_shader

    def _set_pbr_specular_glossiness_specular(self, pbr_specular_glossiness):
        specular_glossiness_texture = pbr_specular_glossiness.get_specular_glossiness_texture()

        specular_factor = tuple(pbr_specular_glossiness.get_specular_factor())
        if not specular_glossiness_texture:
            self._specular_color.Set(specular_factor)
        else:
            scale_factor = (specular_factor[0], specular_factor[1], specular_factor[2], 1)
            destination = specular_glossiness_texture.write_to_directory(self._output_directory, GLTFImage.ImageColorChannels.RGB, "specular")

            self._uv_texture("specularTexture", specular_glossiness_texture, destination, scale_factor, self._specular_color, "rgb")
            """
            usd_uv_texture = USDUVTexture("specularTexture", self._stage, self._usd_material._usd_material, specular_glossiness_texture, [self._st0, self._st1])
            usd_uv_texture._file_asset.Set(destination)
            usd_uv_texture._scale.Set(scale_factor)
            usd_uv_texture._fallback.Set(scale_factor)
            texture_shader = usd_uv_texture.get_shader()
            texture_shader.CreateOutput('rgb', Sdf.ValueTypeNames.Float3)
            self._specular_color.ConnectToSource(texture_shader, 'rgb')
            """

    def _set_pbr_specular_glossiness_glossiness(self, pbr_specular_glossiness):
        specular_glossiness_texture = pbr_specular_glossiness.get_specular_glossiness_texture()
        roughness_factor = 1 - pbr_specular_glossiness.get_glossiness_factor()
        if not specular_glossiness_texture:
            self._roughness.Set(roughness_factor)
        else:
            destination = specular_glossiness_texture.write_to_directory(self._output_directory, GLTFImage.ImageColorChannels.A, "glossiness")
            scale_factor = (-1, -1, -1, -1)

            self._uv_texture("glossinessTexture", specular_glossiness_texture, destination, scale_factor, self._roughness, "r")
            """
            usd_uv_texture = USDUVTexture("glossinessTexture", self._stage, self._usd_material._usd_material, specular_glossiness_texture, [self._st0, self._st1])
            usd_uv_texture._file_asset.Set(destination)
            usd_uv_texture._bias.Set((1.0, 1.0, 1.0, 1.0))
            usd_uv_texture._scale.Set(scale_factor)
            usd_uv_texture._fallback.Set(scale_factor)
            texture_shader = usd_uv_texture.get_shader()
            texture_shader.CreateOutput('r', Sdf.ValueTypeNames.Float)
            self._roughness.ConnectToSource(texture_shader, 'r')
            """

    def _set_pbr_base_color(self, pbr_metallic_roughness, alpha_mode):
        base_color_texture = pbr_metallic_roughness.base_color_texture
        base_color_scale = pbr_metallic_roughness.base_color_factor
        alpha_mode = alpha_mode or AlphaMode.OPAQUE
        print(alpha_mode)
        # if AlphaMode(alpha_mode) != AlphaMode.OPAQUE:
        #    if AlphaMode(alpha_mode) == AlphaMode.MASK:
        #        print('Alpha Mask not supported in USDPreviewSurface!  Using Alpha Blend...')

        if not base_color_texture:
            self._diffuse_color.Set(tuple(base_color_scale[0:3]))
            if alpha_mode != AlphaMode.OPAQUE:
                self._opacity.Set(base_color_scale[3])
        else:
            if AlphaMode(alpha_mode) == AlphaMode.OPAQUE:
                destination = base_color_texture.write_to_directory(self._output_directory, GLTFImage.ImageColorChannels.RGB)
                scale_factor = (base_color_scale[0], base_color_scale[1], base_color_scale[2], base_color_scale[3])
            else:
                destination = base_color_texture.write_to_directory(self._output_directory, GLTFImage.ImageColorChannels.RGBA)
                scale_factor = tuple(base_color_scale[0:4])

            texture_shader = self._uv_texture("baseColorTexture", base_color_texture, destination, scale_factor, self._diffuse_color, "rgb")
            if AlphaMode(alpha_mode) != AlphaMode.OPAQUE:
                texture_shader.CreateOutput("a", Sdf.ValueTypeNames.Float)
                self._opacity.ConnectToSource(texture_shader, "a")
            """
            usd_uv_texture = USDUVTexture("baseColorTexture", self._stage, self._usd_material._usd_material, base_color_texture, [self._st0, self._st1])
            usd_uv_texture._file_asset.Set(destination)
            usd_uv_texture._scale.Set(scale_factor)
            usd_uv_texture._fallback.Set(scale_factor)
            texture_shader = usd_uv_texture.get_shader()
            texture_shader.CreateOutput('rgb', Sdf.ValueTypeNames.Float3)
            texture_shader.CreateOutput('a', Sdf.ValueTypeNames.Float)
            self._diffuse_color.ConnectToSource(texture_shader, 'rgb')
            if AlphaMode(alpha_mode) != AlphaMode.OPAQUE:
                self._opacity.ConnectToSource(texture_shader, 'a')
            """

    def _set_pbr_metallic(self, pbr_metallic_roughness):
        metallic_roughness_texture = pbr_metallic_roughness.metallic_roughness_texture
        metallic_factor = pbr_metallic_roughness.metallic_factor
        if not metallic_roughness_texture or metallic_factor == 0:
            self._metallic.Set(metallic_factor)
        else:
            scale_texture = None
            scale_factor = tuple([metallic_factor] * 4)
            usd_uv_texture = USDUVTexture("metallicTexture", self._stage, self._usd_material._usd_material, metallic_roughness_texture, [self._st0, self._st1])
            if self._scale_texture:
                scale_texture = scale_factor
                usd_uv_texture._scale.Set(tuple([1.0] * 4))
            else:
                usd_uv_texture._scale.Set(scale_factor)
            destination = metallic_roughness_texture.write_to_directory(self._output_directory, GLTFImage.ImageColorChannels.B, "metallic", scale_texture)

            usd_uv_texture._file_asset.Set(destination)
            usd_uv_texture._fallback.Set(scale_factor)
            texture_shader = usd_uv_texture.get_shader()
            texture_shader.CreateOutput("r", Sdf.ValueTypeNames.Float)
            self._metallic.ConnectToSource(texture_shader, "r")

    def _set_pbr_roughness(self, pbr_metallic_roughness):
        metallic_roughness_texture = pbr_metallic_roughness.metallic_roughness_texture
        roughness_factor = pbr_metallic_roughness.roughness_factor
        if not metallic_roughness_texture or roughness_factor == 0:
            self._roughness.Set(roughness_factor)
        else:
            scale_texture = None
            scale_factor = tuple([roughness_factor] * 4)
            usd_uv_texture = USDUVTexture("roughnessTexture", self._stage, self._usd_material._usd_material, metallic_roughness_texture, [self._st0, self._st1])
            if self._scale_texture:
                scale_texture = scale_factor
                usd_uv_texture._scale.Set(tuple([1.0] * 4))
            else:
                usd_uv_texture._scale.Set(scale_factor)

            destination = metallic_roughness_texture.write_to_directory(self._output_directory, GLTFImage.ImageColorChannels.G, "roughness", scale_texture)
            usd_uv_texture._file_asset.Set(destination)
            usd_uv_texture._fallback.Set(scale_factor)
            texture_shader = usd_uv_texture.get_shader()
            texture_shader.CreateOutput("r", Sdf.ValueTypeNames.Float)
            self._roughness.ConnectToSource(texture_shader, "r")


class USDPrimvarReaderFloat2(object):
    def __init__(self, stage, material_path, var_name):
        primvar = UsdShade.Shader.Define(stage, material_path.AppendChild("primvar_{}".format(var_name)))
        primvar.CreateIdAttr("UsdPrimvarReader_float2")
        primvar.CreateInput("fallback", Sdf.ValueTypeNames.Float2).Set((0, 0))
        primvar.CreateInput("varname", Sdf.ValueTypeNames.Token).Set(var_name)
        self._output = primvar.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    def get_output(self):
        return self._output


class USDUVTextureWrapMode(Enum):
    BLACK = "black"
    CLAMP = "clamp"
    REPEAT = "repeat"
    MIRROR = "mirror"


class TextureWrap(Enum):
    CLAMP_TO_EDGE = 33071
    MIRRORED_REPEAT = 33648
    REPEAT = 10497


class USDUVTexture(object):
    TEXTURE_SAMPLER_WRAP = {
        TextureWrap.CLAMP_TO_EDGE.name: "clamp",
        TextureWrap.MIRRORED_REPEAT.name: "mirror",
        TextureWrap.REPEAT.name: "repeat",
    }

    def __init__(self, name, stage, usd_material, gltf_texture, usd_primvar_st_arr):

        material_path = usd_material.GetPath()

        self._texture_shader = UsdShade.Shader.Define(stage, material_path.AppendChild(name))
        self._texture_shader.CreateIdAttr("UsdUVTexture")

        self._wrap_s = self._texture_shader.CreateInput("wrapS", Sdf.ValueTypeNames.Token)
        self._wrap_s.Set(USDUVTexture.TEXTURE_SAMPLER_WRAP[gltf_texture.get_wrap_s().name])

        self._wrap_t = self._texture_shader.CreateInput("wrapT", Sdf.ValueTypeNames.Token)
        self._wrap_t.Set(USDUVTexture.TEXTURE_SAMPLER_WRAP[gltf_texture.get_wrap_t().name])

        self._bias = self._texture_shader.CreateInput("bias", Sdf.ValueTypeNames.Float4)
        self._bias.Set((0, 0, 0, 0))

        self._scale = self._texture_shader.CreateInput("scale", Sdf.ValueTypeNames.Float4)
        self._scale.Set((1, 1, 1, 1))

        self._file_asset = self._texture_shader.CreateInput("file", Sdf.ValueTypeNames.Asset)
        self._file_asset.Set(gltf_texture.get_image_path())

        self._fallback = self._texture_shader.CreateInput("fallback", Sdf.ValueTypeNames.Float4)
        self._fallback.Set((0, 0, 0, 1))

        self._st = self._texture_shader.CreateInput("st", Sdf.ValueTypeNames.Float2)

        self._st.ConnectToSource(usd_primvar_st_arr[gltf_texture.get_texcoord_index()].get_output())

    def get_shader(self):
        return self._texture_shader


if __name__ == "__main__":
    from pxr import Usd
    from compas_usd import DATA

    # stage = Usd.Stage.CreateNew(os.path.join(DATA, "materials.usda"))
    stage = Usd.Stage.CreateInMemory()

    USDMaterial.from_mdl(stage, os.path.join(DATA, "materials", "grey.mdl"))
    USDMaterial.from_mdl(stage, os.path.join(DATA, "materials", "blue.mdl"))

    material = USDMaterial(stage, "preview_surface")
    preview_surface = USDPreviewSurface(stage, material)

    print(stage.GetRootLayer().ExportToString())

    stage.GetRootLayer().Save()
