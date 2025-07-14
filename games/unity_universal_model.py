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

class UnityUniversalModel:
    def __init__(self,workspace_collection:bpy.types.Collection):
        # (1) 统计全局分支模型
        self.branch_model = BranchModel(workspace_collection=workspace_collection)

        # (2) 抽象每个DrawIB为DrawIBModel
        self.draw_ib_draw_ib_model_dict:dict[str,DrawIBModel] = {}
        self.parse_draw_ib_draw_ib_model_dict()

        # (3) 生成Mod的ini
        


    def parse_draw_ib_draw_ib_model_dict(self):
        '''
        根据obj的命名规则，推导出DrawIB并抽象为DrawIBModel
        如果用户用不到某个DrawIB的话，就可以隐藏掉对应的obj
        隐藏掉的obj就不会被统计生成DrawIBModel，做到只导入模型，不生成Mod的效果。
        TODO 这里要在DrawIBModel中改变代码并新增每个Component里的obj的ib和category_buf_dict读取
        '''
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
            draw_ib_model = DrawIBModel(draw_ib=draw_ib,branch_model=self.branch_model)
            self.draw_ib_draw_ib_model_dict[draw_ib] = draw_ib_model
            
            
