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






def ImprotFromWorkSpace(self, context):
    import_drawib_aliasname_folder_path_dict = ConfigUtils.get_import_drawib_aliasname_folder_path_dict_with_first_match_type()
    print(import_drawib_aliasname_folder_path_dict)

    workspace_collection = CollectionUtils.new_workspace_collection()

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

        draw_ib_collection = CollectionUtils.new_draw_ib_collection(collection_name=draw_ib_aliasname)
        workspace_collection.children.link(draw_ib_collection)

        part_count = 1
        for prefix in import_prefix_list:
            component_name = "Component " + str(part_count)
            component_collection = CollectionUtils.new_component_collection(component_name=component_name)
            defualt_switch_collection = CollectionUtils.new_switch_collection(collection_name="default")

            fmt_file_path = os.path.join(import_folder_path, prefix + ".fmt")
            mbf = MigotoBinaryFile(fmt_path=fmt_file_path)
            obj_result = MeshImportUtils.create_mesh_obj_from_mbf(mbf=mbf)
            defualt_switch_collection.objects.link(obj_result)
            component_collection.children.link(defualt_switch_collection)
            draw_ib_collection.children.link(component_collection)

            part_count = part_count + 1

    bpy.context.scene.collection.children.link(workspace_collection)

    # Select all objects under collection (因为用户习惯了导入后就是全部选中的状态). 
    CollectionUtils.select_collection_objects(workspace_collection)



class DBMTImportAllFromCurrentWorkSpace(bpy.types.Operator):
    bl_idname = "dbmt.import_all_from_workspace"
    bl_label = "一键导入当前工作空间内容"
    bl_description = "一键导入当前工作空间文件夹下所有的DrawIB对应的模型为分支集合架构"

    def execute(self, context):
        if GlobalConfig.workspacename == "":
            self.report({"ERROR"},"Please select your WorkSpace in DBMT before import.")
        elif not os.path.exists(GlobalConfig.path_workspace_folder()):
            self.report({"ERROR"},"Please select a correct WorkSpace in DBMT before import " + GlobalConfig.path_workspace_folder())
        else:
            TimerUtils.Start("ImportFromWorkSpace")
            ImprotFromWorkSpace(self,context)
            TimerUtils.End("ImportFromWorkSpace")
        return {'FINISHED'}