import bpy
import copy

from ..utils.log_utils import LOG
from ..utils.collection_utils import CollectionUtils, CollectionColor
from ..utils.config_utils import ConfigUtils

from ..migoto.migoto_format import M_Key, ObjDataModel, M_DrawIndexed, M_Condition,D3D11GameType
from ..config.import_config import ImportConfig
from ..generate_mod.m_counter import M_Counter
from .draw_ib_model import DrawIBModel

from .branch_model import BranchModel

class UnityCSModel:
    '''
    全新Mod架构设计
    1.Mod不再以DrawIB为单位，整个Mod可包含多个DrawIB。
    2.分支按键改为全局统计，不再以每个DrawIB为单位。
    '''
    def __init__(self,workspace_collection:bpy.types.Collection):
        self.branch_model = BranchModel(workspace_collection=workspace_collection)

        # (2) 根据obj的命名规则，推导出DrawIB并抽象为DrawIBModel
        # 这里要在DrawIBModel中改变代码并新增每个Component里的obj的ib和category_buf_dict读取
        self.draw_ib_draw_ib_model_dict = {}
        self.parse_draw_ib_draw_ib_model_dict()

    def parse_draw_ib_draw_ib_model_dict(self):
        draw_ib_component_count_list = {}

        for obj_data_model in self.branch_model.ordered_draw_obj_data_model_list:
            draw_ib = obj_data_model.draw_ib
            component_count = obj_data_model.component_count

            component_count_list = []
            if draw_ib in draw_ib_component_count_list:
                component_count_list = draw_ib_component_count_list[draw_ib]
            
            if component_count not in component_count_list:
                component_count_list.append(component_count)

            component_count_list.sort()
            
            draw_ib_component_count_list[draw_ib] = component_count_list
        
        print(draw_ib_component_count_list)

        for draw_ib in draw_ib_component_count_list.keys():
            draw_ib_model = DrawIBModel(draw_ib=draw_ib)
            self.draw_ib_draw_ib_model_dict[draw_ib] = draw_ib_model
            
            
