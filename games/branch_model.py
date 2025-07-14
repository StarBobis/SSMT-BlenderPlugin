import bpy
import copy

from ..utils.obj_utils import ObjUtils
from ..utils.log_utils import LOG
from ..utils.collection_utils import CollectionUtils, CollectionColor
from ..utils.config_utils import ConfigUtils

from ..migoto.migoto_format import M_Key, ObjDataModel, M_Condition, D3D11GameType
from ..generate_mod.m_counter import M_Counter

from ..generate_mod.m_export import get_buffer_ib_vb_fast

'''
分支模型

也就是我们的基于集合嵌套的按键开关与按键切换架构。
分支按键使用此模型进行全局统计，不再以每个DrawIB为单位。
'''
class BranchModel:

    def __init__(self,workspace_collection:bpy.types.Collection):
        # 初始化基础属性
        self.keyname_mkey_dict:dict[str,M_Key] = {} # 全局按键名称和按键属性字典

        self.ordered_draw_obj_data_model_list:list[ObjDataModel] = [] # 全局obj_model列表，主要是obj_model里装了每个obj的生效条件。

        # (1)统计当前工作空间集合下，每个obj的生效条件
        self.parse_current_collection(current_collection=workspace_collection,chain_key_list=[])

        print("当前BranchModel的obj总数量: " + str(len(self.ordered_draw_obj_data_model_list)))
        for obj_data_model in self.ordered_draw_obj_data_model_list:
            print("DrawIB:" + obj_data_model.draw_ib + " Component: " + str(obj_data_model.component_count) + " AliasName: " + obj_data_model.obj_alias_name)
        

    def parse_current_collection(self,current_collection:bpy.types.Collection,chain_key_list:list[M_Key]):
        
        children_collection_list:list[bpy.types.Collection] = current_collection.children

        switch_collection_list:list[bpy.types.Collection] = []

        for unknown_collection in children_collection_list:
            '''
            跳过不可见的集合，因为集合架构中不可见的集合相当于不生效。
            '''
            if not CollectionUtils.is_collection_visible(unknown_collection.name):
                LOG.info("Skip " + unknown_collection.name + " because it's invisiable.")
                continue
            
            # 首先要判断是【组集合】还是【按键开关集合】
            # 随后调用相应的处理逻辑
            # 最后处理【按键切换集合】
            if unknown_collection.color_tag == CollectionColor.GroupCollection:
                '''
                如果子集合是【组集合】则不进行任何处理直接传递解析下去
                '''
                self.parse_current_collection(current_collection=unknown_collection,chain_key_list=chain_key_list)
            elif unknown_collection.color_tag == CollectionColor.ToggleCollection:
                '''
                如果子集合是【按键开关集合】则要添加一个Key，更新全局Key字典，更新Key列表并传递解析下去
                '''
                m_key = M_Key()
                current_add_key_index = len(self.keyname_mkey_dict.keys())
                m_key.key_name = "$swapkey" + str(M_Counter.global_key_index)
                # LOG.info("设置KEYname: " + m_key.key_name)

                m_key.value_list = [0,1]
                m_key.key_value = ConfigUtils.get_mod_switch_key(M_Counter.global_key_index)

                # 创建的key要加入全局key列表
                self.keyname_mkey_dict[m_key.key_name] = m_key

                if len(self.keyname_mkey_dict.keys()) > current_add_key_index:
                    # LOG.info("Global Key Index ++")
                    M_Counter.global_key_index = M_Counter.global_key_index + 1

                # 创建的key要加入chain_key_list传递下去
                # 因为传递解析下去的话，要让这个key生效，而又因为它是按键开关key，所以value为1生效，所以tmp_value设为1
                chain_tmp_key = copy.deepcopy(m_key)
                chain_tmp_key.tmp_value = 1

                tmp_chain_key_list = copy.deepcopy(chain_key_list)
                tmp_chain_key_list.append(chain_tmp_key)

                # 递归解析
                self.parse_current_collection(current_collection=unknown_collection,chain_key_list=tmp_chain_key_list)
            elif unknown_collection.color_tag == CollectionColor.SwitchCollection:
                '''
                如果子集合是【按键切换集合】则加入【按键切换集合】的列表，统一处理，不在这儿处理。
                '''
                switch_collection_list.append(unknown_collection)
        
        if len(switch_collection_list) != 0:
            '''
            如果【按键切换集合】的列表不为空，则我们需要添加一个key，并且对每一个集合进行传递
            如果【按键切换集合】只有一个，则视为【组集合】直接传递，否则添加key后对每一个集合进行传递
            '''
            if len(switch_collection_list) == 1:
                # 视为【组集合】进行处理
                for switch_collection in switch_collection_list:
                    self.parse_current_collection(current_collection=switch_collection,chain_key_list=chain_key_list)
            else:
                # 创建并添加一个key
                m_key = M_Key()
                current_add_key_index = len(self.keyname_mkey_dict.keys())
          
                m_key.key_name = "$swapkey" + str(M_Counter.global_key_index)
                # LOG.info("设置KEYname: " + m_key.key_name)
                m_key.value_list = list(range(len(switch_collection_list)))
                m_key.key_value = ConfigUtils.get_mod_switch_key(M_Counter.global_key_index)

                # 创建的key要加入全局key列表
                self.keyname_mkey_dict[m_key.key_name] = m_key

                if len(self.keyname_mkey_dict.keys()) > current_add_key_index:
                    # LOG.info("Global Key Index ++")
                    M_Counter.global_key_index = M_Counter.global_key_index + 1

                key_tmp_value = 0
                for switch_collection in switch_collection_list:
                    # 创建的key要加入chain_key_list传递下去
                    # 因为传递解析下去的话，要让这个key生效，而又因为它是按键开关key，所以value为1生效，所以tmp_value设为1
                    chain_tmp_key = copy.deepcopy(m_key)
                    chain_tmp_key.tmp_value = key_tmp_value
                    tmp_chain_key_list = copy.deepcopy(chain_key_list)
                    tmp_chain_key_list.append(chain_tmp_key)

                    key_tmp_value = key_tmp_value + 1
                    self.parse_current_collection(current_collection=switch_collection,chain_key_list=tmp_chain_key_list)

        # 处理obj
        for obj in current_collection.objects:
            '''
            每个obj都必须添加条件，可是怎么样能知道当前条件是怎样的呢
            '''
            if obj.type == 'MESH' and obj.hide_get() == False:
                
                # print("当前处理物体:" + obj.name + " 生效Key条件:")
                # for chain_key in chain_key_list:
                    # print(chain_key)

                obj_model = ObjDataModel(obj_name=obj.name)
                obj_model.condition = M_Condition(work_key_list=copy.deepcopy(chain_key_list)) 

                # 这里每遇到一个obj，都把这个obj加入顺序渲染列表
                self.ordered_draw_obj_data_model_list.append(obj_model)
                # LOG.newline()


    def get_buffered_obj_data_model_list_by_draw_ib_and_game_type(self,draw_ib:str,d3d11_game_type:D3D11GameType):
        '''
        (1) 读取obj的category_buffer
        (2) 读取obj的ib
        (3) 设置到最终的ordered_draw_obj_model_list
        '''
        __obj_name_ib_dict:dict[str,list] = {} 
        __obj_name_category_buffer_list_dict:dict[str,list] =  {} 

        obj_name_obj_model_cache_dict:dict[str,ObjDataModel] = {}

        for obj_model in self.ordered_draw_obj_data_model_list:

            # 只统计给定DrawIB的数据
            if obj_model.draw_ib != draw_ib:
                continue

            obj_name = obj_model.obj_name

            obj = bpy.data.objects[obj_name]
            
            obj_model = obj_name_obj_model_cache_dict.get(obj_name,None)
            if obj_model is not None:
                LOG.info("Using cached model for " + obj_name)
                __obj_name_ib_dict[obj.name] = obj_model.ib
                __obj_name_category_buffer_list_dict[obj.name] = obj_model.category_buffer_dict
            else:
                # 选中当前obj对象
                bpy.context.view_layer.objects.active = obj

                # XXX 我们在导出具体数据之前，先对模型整体的权重进行normalize_all预处理，才能让后续的具体每一个权重的normalize_all更好的工作
                # 使用这个的前提是当前obj中没有锁定的顶点组，所以这里要先进行判断。
                if "Blend" in d3d11_game_type.OrderedCategoryNameList:
                    all_vgs_locked = ObjUtils.is_all_vertex_groups_locked(obj)
                    if not all_vgs_locked:
                        ObjUtils.normalize_all(obj)

                ib, category_buffer_dict, index_vertex_id_dict = get_buffer_ib_vb_fast(d3d11_game_type)
                
                __obj_name_ib_dict[obj.name] = ib
                __obj_name_category_buffer_list_dict[obj.name] = category_buffer_dict

                obj_model = ObjDataModel(obj_name=obj.name)
                obj_model.ib = ib
                obj_model.category_buffer_dict = category_buffer_dict
                obj_name_obj_model_cache_dict[obj_name] = obj_model
        
        final_ordered_draw_obj_model_list:list[ObjDataModel] = [] 

        print(__obj_name_ib_dict.keys())
        
        for obj_model in self.ordered_draw_obj_data_model_list:

            # 只统计给定DrawIB的数据
            if obj_model.draw_ib != draw_ib:
                continue

            obj_name = obj_model.obj_name

            obj_model.ib = __obj_name_ib_dict[obj_name]
            obj_model.category_buffer_dict = __obj_name_category_buffer_list_dict[obj_name]

            final_ordered_draw_obj_model_list.append(copy.deepcopy(obj_model))
        
        return final_ordered_draw_obj_model_list
