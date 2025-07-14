from ..utils.config_utils import *
from .migoto_format import *
from ..utils.collection_utils import *
from ..config.main_config import *
from ..properties.properties_wwmi import Properties_WWMI
from ..properties.properties_import_model import Properties_ImportModel
from ..utils.obj_utils import ExtractedObjectHelper
from ..utils.json_utils import JsonUtils
from ..utils.texture_utils import TextureUtils


import os.path
import bpy
import math

from bpy_extras.io_utils import unpack_list, ImportHelper, axis_conversion
from bpy.props import BoolProperty, StringProperty, CollectionProperty

from .mesh_import_utils import MeshImportUtils
from .migoto_binary_file import MigotoBinaryFile, FMTFile



def ImprotFromWorkSpaceSSMT(self, context):
    '''
    SSMT的全新集合架构的导入实现
    '''
    import_drawib_aliasname_folder_path_dict = ConfigUtils.get_import_drawib_aliasname_folder_path_dict_with_first_match_type()
    print(import_drawib_aliasname_folder_path_dict)


    workspace_collection = CollectionUtils.create_new_collection(collection_name=GlobalConfig.workspacename,color_tag=CollectionColor.Red)

    # 读取时保存每个DrawIB对应的GameType名称到工作空间文件夹下面的Import.json，在导出时使用
    draw_ib_gametypename_dict = {}
    for draw_ib_aliasname,import_folder_path in import_drawib_aliasname_folder_path_dict.items():
        tmp_json = ConfigUtils.read_tmp_json(import_folder_path)
        work_game_type = tmp_json.get("WorkGameType","")
        draw_ib = draw_ib_aliasname.split("_")[0]
        draw_ib_gametypename_dict[draw_ib] = work_game_type

    save_import_json_path = os.path.join(GlobalConfig.path_workspace_folder(),"Import.json")

    JsonUtils.SaveToFile(json_dict=draw_ib_gametypename_dict,filepath=save_import_json_path)
    

    # 开始读取模型数据
    for draw_ib_aliasname,import_folder_path in import_drawib_aliasname_folder_path_dict.items():
        import_prefix_list = ConfigUtils.get_prefix_list_from_tmp_json(import_folder_path)
        if len(import_prefix_list) == 0:
            self.report({'ERROR'},"当前output文件夹"+draw_ib_aliasname+"中的内容暂不支持一键导入分支模型")
            continue

        draw_ib_collection = CollectionUtils.create_new_collection(collection_name=draw_ib_aliasname,color_tag=CollectionColor.Pink,link_to_parent_collection_name=workspace_collection.name)

        part_count = 1
        for prefix in import_prefix_list:
            component_name = "Component " + str(part_count)
            component_collection = CollectionUtils.create_new_collection(collection_name=component_name,color_tag=CollectionColor.Blue, link_to_parent_collection_name=draw_ib_collection.name)


            fmt_file_path = os.path.join(import_folder_path, prefix + ".fmt")
            mbf = MigotoBinaryFile(fmt_path=fmt_file_path)
            obj_result = MeshImportUtils.create_mesh_obj_from_mbf(mbf=mbf)

            component_collection.objects.link(obj_result)

            part_count = part_count + 1

    # 这里先链接SourceCollection，确保它在上面
    bpy.context.scene.collection.children.link(workspace_collection)

    # Select all objects under collection (因为用户习惯了导入后就是全部选中的状态). 
    CollectionUtils.select_collection_objects(workspace_collection)


class SSMTImportAllFromCurrentWorkSpace(bpy.types.Operator):
    bl_idname = "ssmt.import_all_from_workspace_v2"
    bl_label = "一键导入当前工作空间内容"
    bl_description = "一键导入当前工作空间文件夹下所有的DrawIB对应的模型为SSMT集合架构"

    def execute(self, context):
        if GlobalConfig.workspacename == "":
            self.report({"ERROR"},"Please select your WorkSpace in SSMT before import.")
        elif not os.path.exists(GlobalConfig.path_workspace_folder()):
            self.report({"ERROR"},"Please select a correct WorkSpace in SSMT before import " + GlobalConfig.path_workspace_folder())
        else:
            TimerUtils.Start("ImportFromWorkSpace")
            ImprotFromWorkSpaceSSMT(self,context)
            TimerUtils.End("ImportFromWorkSpace")
        return {'FINISHED'}
    




def ImprotFromWorkSpaceSSMTV3(self, context):
    '''
    SSMT第三个版本集合架构的导入实现
    第三个版本变更主要是为了支持一个按键控制多个DrawIB中的模型
    同时简化工作空间集合的架构
    '''
    import_drawib_aliasname_folder_path_dict = ConfigUtils.get_import_drawib_aliasname_folder_path_dict_with_first_match_type()
    print(import_drawib_aliasname_folder_path_dict)

    workspace_collection = CollectionUtils.create_new_collection(collection_name=GlobalConfig.workspacename,color_tag=CollectionColor.Red)

    # 读取时保存每个DrawIB对应的GameType名称到工作空间文件夹下面的Import.json，在导出时使用
    draw_ib_gametypename_dict = {}
    for draw_ib_aliasname,import_folder_path in import_drawib_aliasname_folder_path_dict.items():
        tmp_json = ConfigUtils.read_tmp_json(import_folder_path)
        work_game_type = tmp_json.get("WorkGameType","")
        draw_ib = draw_ib_aliasname.split("_")[0]
        draw_ib_gametypename_dict[draw_ib] = work_game_type

    save_import_json_path = os.path.join(GlobalConfig.path_workspace_folder(),"Import.json")

    JsonUtils.SaveToFile(json_dict=draw_ib_gametypename_dict,filepath=save_import_json_path)
    

    # 开始读取模型数据
    for draw_ib_aliasname,import_folder_path in import_drawib_aliasname_folder_path_dict.items():
        print("Importing DrawIB:", draw_ib_aliasname)

        draw_ib = draw_ib_aliasname.split("_")[0]
        alias_name = draw_ib_aliasname.split("_")[1]
        if alias_name == "":
            alias_name = "Original"

        import_prefix_list = ConfigUtils.get_prefix_list_from_tmp_json(import_folder_path)
        if len(import_prefix_list) == 0:
            self.report({'ERROR'},"当前output文件夹"+draw_ib_aliasname+"中的内容暂不支持一键导入分支模型")
            continue

        part_count = 1
        for prefix in import_prefix_list:
            fmt_file_path = os.path.join(import_folder_path, prefix + ".fmt")
            mbf = MigotoBinaryFile(fmt_path=fmt_file_path,mesh_name=draw_ib + "-" + str(part_count) + "-" + alias_name)
            obj_result = MeshImportUtils.create_mesh_obj_from_mbf(mbf=mbf)
            workspace_collection.objects.link(obj_result)
            part_count = part_count + 1

    # 这里先链接SourceCollection，确保它在上面
    bpy.context.scene.collection.children.link(workspace_collection)

    # Select all objects under collection (因为用户习惯了导入后就是全部选中的状态). 
    CollectionUtils.select_collection_objects(workspace_collection)


class SSMTImportAllFromCurrentWorkSpaceV3(bpy.types.Operator):
    bl_idname = "ssmt.import_all_from_workspace_v3"
    bl_label = "一键导入当前工作空间内容(内测版勿使用)"
    bl_description = "一键导入当前工作空间文件夹下所有的DrawIB对应的模型为SSMT集合架构"

    def execute(self, context):
        if GlobalConfig.workspacename == "":
            self.report({"ERROR"},"Please select your WorkSpace in SSMT before import.")
        elif not os.path.exists(GlobalConfig.path_workspace_folder()):
            self.report({"ERROR"},"Please select a correct WorkSpace in SSMT before import " + GlobalConfig.path_workspace_folder())
        else:
            TimerUtils.Start("ImportFromWorkSpace")
            ImprotFromWorkSpaceSSMTV3(self,context)
            TimerUtils.End("ImportFromWorkSpace")
        return {'FINISHED'}
    