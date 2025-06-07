import bpy

from ..utils.command_utils import *
from ..generate_mod.m_drawib_model import DrawIBModel
from ..generate_mod.m_drawib_model_wwmi import DrawIBModelWWMI
from ..generate_mod.ini_model_unity import *
from ..generate_mod.ini_model_hsr import M_HSRIniModel
from ..generate_mod.ini_model_wwmi import M_WWMIIniModel
from ..generate_mod.ini_model_ctx import M_CTX_IniModel
from ..generate_mod.ini_model_unity_v2 import M_UnityIniModelV2

from ..generate_mod.drawib_model_universal import DrawIBModelUniversal


class SSMTGenerateModUnityVS(bpy.types.Operator):
    bl_idname = "ssmt.generate_mod_unity_vs"
    bl_label = "生成Mod(SSMT Test)"
    bl_description = "一键导出当前工作空间集合中的Mod，隐藏显示的模型不会被导出，隐藏的DrawIB为名称的集合不会被导出。使用前确保取消隐藏所有要导出的模型以及集合"

    def execute(self, context):
        TimerUtils.Start("GenerateMod UnityVS")

        M_UnityIniModelV2.initialzie()

        workspace_collection = bpy.context.collection

        result = CollectionUtils.is_valid_ssmt_workspace_collection(workspace_collection)
        if result != "":
            self.report({'ERROR'},result)
            return {'FINISHED'}
        
        for draw_ib_collection in workspace_collection.children:
            # Skip hide collection.
            if not CollectionUtils.is_collection_visible(draw_ib_collection.name):
                continue

            # get drawib
            draw_ib_alias_name = CollectionUtils.get_clean_collection_name(draw_ib_collection.name)
            draw_ib = draw_ib_alias_name.split("_")[0]
            draw_ib_model = DrawIBModelUniversal(draw_ib_collection,False)
            M_UnityIniModelV2.drawib_drawibmodel_dict[draw_ib] = draw_ib_model

        # ModModel填充完毕后，开始输出Mod
        M_UnityIniModelV2.generate_unity_vs_config_ini()

        self.report({'INFO'},"Generate Mod Success!")
        CommandUtils.OpenGeneratedModFolder()

        TimerUtils.End("GenerateMod UnityVS")
        return {'FINISHED'}



class DBMTExportUnityVSModToWorkSpaceSeperated(bpy.types.Operator):
    bl_idname = "dbmt.export_unity_vs_mod_to_workspace_seperated"
    bl_label = "生成Mod"
    bl_description = "一键导出当前工作空间集合中的Mod，隐藏显示的模型不会被导出，隐藏的DrawIB为名称的集合不会被导出。"

    def execute(self, context):
        TimerUtils.Start("GenerateMod UnityVS Fast")

        M_UnityIniModel.initialzie()

        workspace_collection = bpy.context.collection

        result = CollectionUtils.is_valid_workspace_collection(workspace_collection)
        if result != "":
            self.report({'ERROR'},result)
            return {'FINISHED'}
        
        for draw_ib_collection in workspace_collection.children:
            # Skip hide collection.
            if not CollectionUtils.is_collection_visible(draw_ib_collection.name):
                continue

            # get drawib
            draw_ib_alias_name = CollectionUtils.get_clean_collection_name(draw_ib_collection.name)
            draw_ib = draw_ib_alias_name.split("_")[0]
            draw_ib_model = DrawIBModel(draw_ib_collection,False)
            M_UnityIniModel.drawib_drawibmodel_dict[draw_ib] = draw_ib_model

        # ModModel填充完毕后，开始输出Mod
        M_UnityIniModel.generate_unity_vs_config_ini()

        self.report({'INFO'},"Generate Mod Success!")
        CommandUtils.OpenGeneratedModFolder()

        TimerUtils.End("GenerateMod UnityVS Fast")
        return {'FINISHED'}


# 崩铁3.2专用...
class ExportModHonkaiStarRail32(bpy.types.Operator):
    bl_idname = "dbmt.export_mod_hsr_32"
    bl_label = "生成HSR Mod"
    bl_description = "一键导出当前工作空间集合中的Mod，隐藏显示的模型不会被导出，隐藏的DrawIB为名称的集合不会被导出。"

    def execute(self, context):
        M_HSRIniModel.initialzie()

        workspace_collection = bpy.context.collection

        result = CollectionUtils.is_valid_workspace_collection(workspace_collection)
        if result != "":
            self.report({'ERROR'},result)
            return {'FINISHED'}
        
        for draw_ib_collection in workspace_collection.children:
            # Skip hide collection.
            if not CollectionUtils.is_collection_visible(draw_ib_collection.name):
                continue

            # get drawib
            draw_ib_alias_name = CollectionUtils.get_clean_collection_name(draw_ib_collection.name)
            draw_ib = draw_ib_alias_name.split("_")[0]
            draw_ib_model = DrawIBModel(draw_ib_collection,False)
            M_HSRIniModel.drawib_drawibmodel_dict[draw_ib] = draw_ib_model

        # ModModel填充完毕后，开始输出Mod
        M_HSRIniModel.generate_unity_cs_config_ini()

        self.report({'INFO'},"生成Mod成功!")
        CommandUtils.OpenGeneratedModFolder()
        
        return {'FINISHED'}
    

class DBMTExportUnityCSModToWorkSpaceSeperated(bpy.types.Operator):
    bl_idname = "dbmt.export_unity_cs_mod_to_workspace_seperated"
    bl_label = "生成Mod"
    bl_description = "一键导出当前工作空间集合中的Mod，隐藏显示的模型不会被导出，隐藏的DrawIB为名称的集合不会被导出。"

    def execute(self, context):
        TimerUtils.Start("GenerateMod UnityCS")

        M_UnityIniModel.initialzie()

        workspace_collection = bpy.context.collection

        result = CollectionUtils.is_valid_workspace_collection(workspace_collection)
        if result != "":
            self.report({'ERROR'},result)
            return {'FINISHED'}
        
        for draw_ib_collection in workspace_collection.children:
            # Skip hide collection.
            if not CollectionUtils.is_collection_visible(draw_ib_collection.name):
                continue

            # get drawib
            draw_ib_alias_name = CollectionUtils.get_clean_collection_name(draw_ib_collection.name)
            draw_ib = draw_ib_alias_name.split("_")[0]
            draw_ib_model = DrawIBModel(draw_ib_collection,False)
            M_UnityIniModel.drawib_drawibmodel_dict[draw_ib] = draw_ib_model

        # ModModel填充完毕后，开始输出Mod
        M_UnityIniModel.generate_unity_cs_config_ini()

        self.report({'INFO'},"Generate Mod Success!")

        CommandUtils.OpenGeneratedModFolder()

        TimerUtils.End("GenerateMod UnityCS")
        return {'FINISHED'}
    
    
# WWMI
class GenerateModWWMI(bpy.types.Operator):
    bl_idname = "herta.export_mod_wwmi"
    bl_label = "生成WWMI格式Mod"
    bl_description = "一键导出当前工作空间集合中的Mod，隐藏显示的模型不会被导出，隐藏的DrawIB为名称的集合不会被导出。"

    def execute(self, context):
        TimerUtils.Start("GenerateMod WWMI")

        M_WWMIIniModel.initialzie()

        workspace_collection = bpy.context.collection

        result = CollectionUtils.is_valid_workspace_collection(workspace_collection)
        if result != "":
            self.report({'ERROR'},result)
            return {'FINISHED'}
        
        for draw_ib_collection in workspace_collection.children:
            # Skip hide collection.
            if not CollectionUtils.is_collection_visible(draw_ib_collection.name):
                continue

            # get drawib
            draw_ib_alias_name = CollectionUtils.get_clean_collection_name(draw_ib_collection.name)
            draw_ib = draw_ib_alias_name.split("_")[0]
            draw_ib_model = DrawIBModelWWMI(draw_ib_collection)
            M_WWMIIniModel.drawib_drawibmodel_dict[draw_ib] = draw_ib_model

        # ModModel填充完毕后，开始输出Mod
        M_WWMIIniModel.generate_unreal_vs_config_ini()

        self.report({'INFO'},"Generate Mod Success!")

        CommandUtils.OpenGeneratedModFolder()

        TimerUtils.End("GenerateMod WWMI")
        return {'FINISHED'}

class GenerateModYYSLS(bpy.types.Operator):
    bl_idname = "dbmt.generate_mod_yysls"
    bl_label = "生成Mod"
    bl_description = "一键导出当前工作空间集合中的Mod，隐藏显示的模型不会被导出，隐藏的DrawIB为名称的集合不会被导出。"

    def execute(self, context):
        TimerUtils.Start("GenerateMod YYSLS")

        M_CTX_IniModel.initialzie()

        workspace_collection = bpy.context.collection

        result = CollectionUtils.is_valid_workspace_collection(workspace_collection)
        if result != "":
            self.report({'ERROR'},result)
            return {'FINISHED'}
        
        for draw_ib_collection in workspace_collection.children:
            # Skip hide collection.
            if not CollectionUtils.is_collection_visible(draw_ib_collection.name):
                continue

            # get drawib
            draw_ib_alias_name = CollectionUtils.get_clean_collection_name(draw_ib_collection.name)
            draw_ib = draw_ib_alias_name.split("_")[0]
            draw_ib_model = DrawIBModel(draw_ib_collection,False)
            M_CTX_IniModel.drawib_drawibmodel_dict[draw_ib] = draw_ib_model

        # ModModel填充完毕后，开始输出Mod
        M_CTX_IniModel.generate_unity_vs_config_ini()

        self.report({'INFO'},"生成 YYSLS Mod完成")

        CommandUtils.OpenGeneratedModFolder()

        TimerUtils.End("GenerateMod YYSLS")
        return {'FINISHED'}