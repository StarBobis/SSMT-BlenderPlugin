import numpy
import struct
import re

from .m_export import get_buffer_ib_vb_fast

from ..migoto.migoto_format import *

from ..utils.collection_utils import *
from ..config.main_config import *
from ..utils.json_utils import *
from ..utils.timer_utils import *
from ..utils.migoto_utils import Fatal
from ..utils.obj_utils import ObjUtils

from ..utils.obj_utils import ExtractedObject, ExtractedObjectHelper



class M_DrawIndexed:

    def __init__(self) -> None:
        self.DrawNumber = ""

        # 绘制起始位置
        self.DrawOffsetIndex = "" 

        self.DrawStartIndex = "0"

        # 代表一个obj具体的draw_indexed
        self.AliasName = "" 

        # 代表这个obj的顶点数
        self.UniqueVertexCount = 0 
    
    def get_draw_str(self) ->str:
        return "drawindexed = " + self.DrawNumber + "," + self.DrawOffsetIndex +  "," + self.DrawStartIndex


class TextureReplace:
    def  __init__(self):
        self.resource_name = ""
        self.filter_index = 0
        self.hash = ""
        self.style = ""
        

class ModelCollection:
    def __init__(self):
        self.type = ""
        self.model_collection_name = ""
        self.obj_name_list = []


# 这个代表了一个DrawIB的Mod导出模型
# 后面的Mod导出都可以调用这个模型来进行业务逻辑部分
'''
TODO 这种DrawIBModel的形式，无法实现方便的架构变更
目前的思路是创建另一个WWMI专用的DrawIBModel，然后在开发过程中把通用的方法抽象成工具类型。
'''
class DrawIBModel:
    # 通过default_factory让每个类的实例的变量分割开来，不再共享类的静态变量
    def __init__(self,draw_ib_collection,merge_objects:bool):
        '''
        根据3Dmigoto的架构设计，每个DrawIB都是一个独立的Mod
        '''
        drawib_collection_name_splits = CollectionUtils.get_clean_collection_name(draw_ib_collection.name).split("_")
        self.draw_ib = drawib_collection_name_splits[0]
        self.draw_ib_alias = drawib_collection_name_splits[1]

        # (1) 读取工作空间中配置文件的配置项
        self.category_hash_dict = {}
        self.match_first_index_list = []
        self.part_name_list = []
        self.vertex_limit_hash = ""
        self.extract_gametype_folder_path = ""
        self.PartName_SlotTextureReplaceDict_Dict:dict[str,dict[str,TextureReplace]] = {} # 自动贴图配置项
        self.TextureResource_Name_FileName_Dict:dict[str,str] = {} # 自动贴图配置项
        self.d3d11GameType:D3D11GameType = None
        self.extracted_object:ExtractedObject = None

        self.__read_config_from_workspace()

        # (2) 解析集合架构，获得每个DrawIB中，每个Component对应的obj列表及其相关属性
        self.componentname_modelcollection_list_dict:dict[str,list[ModelCollection]] = {}
        self.__parse_drawib_collection_architecture(draw_ib_collection=draw_ib_collection)

        # (3) 解析当前有多少个key
        self.key_number = 0
        self.__parse_key_number()

        # (4) 根据之前解析集合架构的结果，读取obj对象内容到字典中
        self.__obj_name_ib_dict:dict[str,list] = {} 
        self.__obj_name_category_buffer_list_dict:dict[str,list] =  {} 
        self.obj_name_drawindexed_dict:dict[str,M_DrawIndexed] = {} # 给每个obj的属性统计好，后面就能直接用了。
        self.__obj_name_index_vertex_id_dict:dict[str,dict] = {} # 形态键功能必备
        self.componentname_ibbuf_dict = {} # 每个Component都生成一个IndexBuffer文件，或者所有Component共用一个IB文件。
        self.__categoryname_bytelist_dict = {} # 每个Category都生成一个CategoryBuffer文件。

        self.draw_number = 0 # 每个DrawIB都有总的顶点数，对应CategoryBuffer里的顶点数。
        self.total_index_count = 0 # 每个DrawIB都有总的IndexCount数，也就是所有的IB中的所有顶点索引数量

        self.__parse_obj_name_ib_category_buffer_dict()
        if GlobalConfig.get_game_category() == GameCategory.UnrealVS or GlobalConfig.get_game_category() == GameCategory.UnrealCS: 
            # UnrealVS目前只能一个IB
            self.__read_component_ib_buf_dict_merged()
        elif GlobalConfig.gamename == "IdentityV":
            self.__read_component_ib_buf_dict_merged()
        else:
            self.__read_component_ib_buf_dict_seperated_single()
            
        # 构建每个Category的VertexBuffer
        self.__read_categoryname_bytelist_dict()

        # WWMI专用，因为它非得用到metadata.json的东西
        # 目前只有WWMI会需要读取ShapeKey数据
        # 用于形态键导出
        self.shapekey_offsets = []
        self.shapekey_vertex_ids = []
        self.shapekey_vertex_offsets = []
        if GlobalConfig.gamename == "WWMI":
            self.__read_shapekey_cateogry_buf_dict()
            metadatajsonpath = GlobalConfig.path_extract_gametype_folder(draw_ib=self.draw_ib,gametype_name=self.d3d11GameType.GameTypeName)  + "Metadata.json"
            if os.path.exists(metadatajsonpath):
                self.extracted_object = ExtractedObjectHelper.read_metadata(metadatajsonpath)

        # (5) 导出Buffer文件，Export Index Buffer files, Category Buffer files. (And Export ShapeKey Buffer Files.(WWMI))
        # 用于写出IB时使用
        self.PartName_IBResourceName_Dict = {}
        self.PartName_IBBufferFileName_Dict = {}
        self.combine_partname_ib_resource_and_filename_dict()
        self.write_buffer_files()
    
    def __read_config_from_workspace(self):
        '''
        在一键导入工作空间时，Import.json会记录导入的GameType，在生成Mod时需要用到
        所以这里我们读取Import.json来确定要从哪个提取出来的数据类型文件夹中读取
        然后读取tmp.json来初始化D3D11GameType
        '''
        workspace_import_json_path = os.path.join(GlobalConfig.path_workspace_folder(), "Import.json")
        draw_ib_gametypename_dict = JsonUtils.LoadFromFile(workspace_import_json_path)
        gametypename = draw_ib_gametypename_dict.get(self.draw_ib,"")

        # 新版本中，我们把数据类型的信息写到了tmp.json中，这样我们就能够读取tmp.json中的内容来决定生成Mod时的数据类型了。
        self.extract_gametype_folder_path = GlobalConfig.path_extract_gametype_folder(draw_ib=self.draw_ib,gametype_name=gametypename)
        tmp_json_path = os.path.join(self.extract_gametype_folder_path,"tmp.json")
        if os.path.exists(tmp_json_path):
            self.d3d11GameType:D3D11GameType = D3D11GameType(tmp_json_path)
        else:
            raise Fatal("Can't find your tmp.json for generate mod:" + tmp_json_path)
        
        '''
        读取tmp.json中的内容，后续会用于生成Mod的ini文件
        需要在确定了D3D11GameType之后再执行
        '''
        self.extract_gametype_folder_path = GlobalConfig.path_extract_gametype_folder(draw_ib=self.draw_ib,gametype_name=self.d3d11GameType.GameTypeName)
        tmp_json_path = os.path.join(self.extract_gametype_folder_path,"tmp.json")
        tmp_json_dict = JsonUtils.LoadFromFile(tmp_json_path)

        self.category_hash_dict = tmp_json_dict["CategoryHash"]
        self.import_model_list = tmp_json_dict["ImportModelList"]
        self.match_first_index_list = tmp_json_dict["MatchFirstIndex"]
        self.part_name_list = tmp_json_dict["PartNameList"]
        self.vshash_list = tmp_json_dict.get("VSHashList",[])

        # print(self.partname_textureresourcereplace_dict)
        self.vertex_limit_hash = tmp_json_dict["VertexLimitVB"]
        self.work_game_type = tmp_json_dict["WorkGameType"]

        # 自动贴图依赖于这个字典
        partname_textureresourcereplace_dict:dict[str,str] = tmp_json_dict["PartNameTextureResourceReplaceList"]

        print(tmp_json_path)
        print(partname_textureresourcereplace_dict)
        for partname, texture_resource_replace_list in partname_textureresourcereplace_dict.items():
            slot_texture_replace_dict = {}
            for texture_resource_replace in texture_resource_replace_list:
                splits = texture_resource_replace.split("=")
                slot_name = splits[0].strip()
                texture_filename = splits[1].strip()

                resource_name = "Resource_" + os.path.splitext(texture_filename)[0]

                filename_splits = os.path.splitext(texture_filename)[0].split("_")
                texture_hash = filename_splits[2]

                texture_replace = TextureReplace()
                texture_replace.hash = texture_hash
                texture_replace.resource_name = resource_name
                texture_replace.style = filename_splits[3]

                slot_texture_replace_dict[slot_name] = texture_replace

                self.TextureResource_Name_FileName_Dict[resource_name] = texture_filename

            self.PartName_SlotTextureReplaceDict_Dict[partname] = slot_texture_replace_dict
    
    def __parse_drawib_collection_architecture(self,draw_ib_collection):
        '''
        解析工作空间集合架构，得到方便后续访问使用的抽象数据类型ModelCollection。
        '''

        # LOG.info("DrawIB: " + self.draw_ib)
        # LOG.info("Visiable: " + str(CollectionUtils.is_collection_visible(draw_ib_collection.name)))

        
        for component_collection in draw_ib_collection.children:
            # 从集合名称中获取导出后部位的名称，如果有.001这种自动添加的后缀则去除掉
            component_name = CollectionUtils.get_clean_collection_name(component_collection.name)

            model_collection_list = []
            for m_collection in component_collection.children:
                # 如果模型不可见则跳过。
                if not CollectionUtils.is_collection_visible(m_collection.name):
                    LOG.info("Skip " + m_collection.name + " because it's invisiable.")
                    continue

                # LOG.info("Current Processing Collection: " + m_collection.name)

                # 声明一个model_collection对象
                model_collection = ModelCollection()
                model_collection.model_collection_name = m_collection.name

                # 先根据颜色确定是什么类型的集合 03黄色是开关 04绿色是分支
                model_collection_type = "default"
                if m_collection.color_tag == "COLOR_03":
                    model_collection_type = "switch"
                elif m_collection.color_tag == "COLOR_04":
                    model_collection_type = "toggle"
                model_collection.type = model_collection_type

                # 集合中的模型列表
                for obj in m_collection.objects:
                    # 判断对象是否为网格对象，并且不是隐藏状态
                    if obj.type == 'MESH' and obj.hide_get() == False:
                        model_collection.obj_name_list.append(obj.name)

                model_collection_list.append(model_collection)

            self.componentname_modelcollection_list_dict[component_name] = model_collection_list

    def __parse_key_number(self):
        '''
        提前统计好有多少个Key要声明
        '''
        tmp_number = 0
        for model_collection_list in self.componentname_modelcollection_list_dict.values():
            toggle_number = 0 # 切换
            switch_number = 0 # 开关
            for model_collection in model_collection_list:
                if model_collection.type == "toggle":
                    toggle_number = toggle_number + 1
                elif model_collection.type == "switch":
                    switch_number = switch_number + 1
            
            tmp_number = tmp_number + switch_number
            if toggle_number >= 2:
                tmp_number = tmp_number + 1
        self.key_number = tmp_number

    def __parse_obj_name_ib_category_buffer_dict(self):
        '''
        把之前统计的所有obj都转为ib和category_buffer_dict格式备用
        '''
        for model_collection_list in self.componentname_modelcollection_list_dict.values():
            for model_collection in model_collection_list:
                for obj_name in model_collection.obj_name_list:
                    obj = bpy.data.objects[obj_name]
                    
                    # 选中当前obj对象
                    bpy.context.view_layer.objects.active = obj

                    # XXX 我们在导出具体数据之前，先对模型整体的权重进行normalize_all预处理，才能让后续的具体每一个权重的normalize_all更好的工作
                    # 使用这个的前提是当前obj中没有锁定的顶点组，所以这里要先进行判断。
                    if "Blend" in self.d3d11GameType.OrderedCategoryNameList:
                        all_vgs_locked = ObjUtils.is_all_vertex_groups_locked(obj)
                        if not all_vgs_locked:
                            ObjUtils.normalize_all(obj)

                    ib, category_buffer_dict = get_buffer_ib_vb_fast(self.d3d11GameType)
                    # self.__obj_name_index_vertex_id_dict[obj_name] = index_vertex_id_dict
                    
                    self.__obj_name_ib_dict[obj.name] = ib
                    self.__obj_name_category_buffer_list_dict[obj.name] = category_buffer_dict
                    # self.__obj_name_index_vertex_id_dict[obj.name] = index_vertex_id_dict


    def __read_component_ib_buf_dict_merged(self):
        '''
        一个DrawIB的所有Component共享整体的IB文件。
        也就是一个DrawIB的所有绘制中，所有的MatchFirstIndex都来源于一个IndexBuffer文件。
        是游戏原本的做法，但是不分开的话，一个IndexBuffer文件会遇到135W顶点索引数的上限。
        
        由于在WWMI中只能使用一个IB文件，而在GI、HSR、HI3、ZZZ等Unity游戏中天生就能使用多个IB文件
        所以这里只有WWMI会用到，其它游戏如果不是必要尽量不要用，避免135W左右的顶点索引数限制。
        '''
        vertex_number_ib_offset = 0
        ib_buf = []
        draw_offset = 0
        for component_name, moel_collection_list in self.componentname_modelcollection_list_dict.items():
            for model_collection in moel_collection_list:
                for obj_name in model_collection.obj_name_list:
                    # print("processing: " + obj_name)
                    ib = self.__obj_name_ib_dict.get(obj_name,None)

                    # ib的数据类型是list[int]
                    unique_vertex_number_set = set(ib)
                    unique_vertex_number = len(unique_vertex_number_set)

                    if ib is None:
                        print("Can't find ib object for " + obj_name +",skip this obj process.")
                        continue

                    offset_ib = []
                    for ib_number in ib:
                        offset_ib.append(ib_number + vertex_number_ib_offset)
                    
                    # print("Component name: " + component_name)
                    # print("Draw Offset: " + str(vertex_number_ib_offset))
                    ib_buf.extend(offset_ib)

                    drawindexed_obj = M_DrawIndexed()
                    draw_number = len(offset_ib)
                    drawindexed_obj.DrawNumber = str(draw_number)
                    drawindexed_obj.DrawOffsetIndex = str(draw_offset)
                    drawindexed_obj.UniqueVertexCount = unique_vertex_number
                    drawindexed_obj.AliasName = "[" + model_collection.model_collection_name + "] [" + obj_name + "]  (" + str(unique_vertex_number) + ")"
                    self.obj_name_drawindexed_dict[obj_name] = drawindexed_obj
                    draw_offset = draw_offset + draw_number

                    # Add UniqueVertexNumber to show vertex count in mod ini.
                    # print("Draw Number: " + str(unique_vertex_number))
                    vertex_number_ib_offset = vertex_number_ib_offset + unique_vertex_number

                    # LOG.newline()
        # 累加完毕后draw_offset的值就是总的index_count的值，正好作为WWMI的$object_id
        self.total_index_count = draw_offset

        for component_name, moel_collection_list in self.componentname_modelcollection_list_dict.items():
            # Only export if it's not empty.
            if len(ib_buf) != 0:
                self.componentname_ibbuf_dict[component_name] = ib_buf
            else:
                LOG.warning(self.draw_ib + " collection: " + component_name + " is hide, skip export ib buf.")

    def __read_component_ib_buf_dict_seperated_single(self):
        '''
        Single:每个IB文件都从0开始
        每个Component都有一个单独的IB文件。
        所以每个Component都有135W上限。
        '''
        print("Read Component IB Buffer Dict Seperated Single")
        vertex_number_ib_offset = 0
        total_offset = 0
        for component_name, moel_collection_list in self.componentname_modelcollection_list_dict.items():
            ib_buf = []
            offset = 0
            for model_collection in moel_collection_list:
                for obj_name in model_collection.obj_name_list:
                    # print("processing: " + obj_name)
                    ib = self.__obj_name_ib_dict.get(obj_name,None)

                    # ib的数据类型是list[int]
                    unique_vertex_number_set = set(ib)
                    unique_vertex_number = len(unique_vertex_number_set)

                    if ib is None:
                        print("Can't find ib object for " + obj_name +",skip this obj process.")
                        continue

                    offset_ib = []
                    for ib_number in ib:
                        offset_ib.append(ib_number + vertex_number_ib_offset)
                    
                    # print("Component name: " + component_name)
                    # print("Draw Offset: " + str(vertex_number_ib_offset))
                    ib_buf.extend(offset_ib)

                    drawindexed_obj = M_DrawIndexed()
                    draw_number = len(offset_ib)
                    drawindexed_obj.DrawNumber = str(draw_number)
                    drawindexed_obj.DrawOffsetIndex = str(offset)
                    drawindexed_obj.UniqueVertexCount = unique_vertex_number
                    drawindexed_obj.AliasName = "[" + model_collection.model_collection_name + "] [" + obj_name + "]  (" + str(unique_vertex_number) + ")"
                    self.obj_name_drawindexed_dict[obj_name] = drawindexed_obj
                    offset = offset + draw_number

                    # 鸣潮需要
                    total_offset = total_offset + draw_number

                    # Add UniqueVertexNumber to show vertex count in mod ini.
                    # print("Draw Number: " + str(unique_vertex_number))
                    vertex_number_ib_offset = vertex_number_ib_offset + unique_vertex_number

                    # LOG.newline()
            
            # Only export if it's not empty.
            if len(ib_buf) != 0:
                self.componentname_ibbuf_dict[component_name] = ib_buf
            else:
                LOG.warning(self.draw_ib + " collection: " + component_name + " is hide, skip export ib buf.")

        self.total_index_count = total_offset


    def __read_shapekey_cateogry_buf_dict(self):
        '''
        从模型中读取形态键部分，生成形态键数据所需的Buffer

        TODO 形态键合并问题：
        目前带有形态键的物体如果放到其它部位就会导致形态键炸裂，需要排查原因。
        '''
        # TimerUtils.Start("read shapekey data")

        shapekey_index_list = []
        shapekey_data = {}

        vertex_count_offset = 0

        for obj_name, drawindexed_obj in self.obj_name_drawindexed_dict.items():
            obj = bpy.data.objects[obj_name]
            print("Processing obj: " + obj_name)
            mesh = obj.data
            
            # 如果这个obj的mesh没有形态键，那就直接跳过不处理
            mesh_shapekeys = mesh.shape_keys
            if mesh_shapekeys is None:
                print("obj: " + obj_name + " 不含有形态键，跳过处理")
                # 即使跳过了这个obj，这个顶点数偏移依然要加上，否则得到的结果是不正确的
                # 测试过了，这个地方和形态键合并无关
                vertex_count_offset = vertex_count_offset + len(mesh.vertices)
                # print("vertex_count_offset: " + str(vertex_count_offset))
                continue   
            else:
                print(obj_name + "'s shapekey number: " + str(len(mesh.shape_keys.key_blocks)))

            base_data = mesh_shapekeys.key_blocks['Basis'].data
            for shapekey in mesh_shapekeys.key_blocks:
                # 截取形态键名称中的形态键shapekey_id，获取不到就跳过
                shapekey_pattern = re.compile(r'.*(?:deform|custom)[_ -]*(\d+).*')
                match = shapekey_pattern.findall(shapekey.name.lower())
                if len(match) == 0:
                    # print("当前形态键名称:" +shapekey.name + " 不是以Deform开头的，进行跳过")
                    continue
                # else:
                #     print(shapekey.name)

                shapekey_index = int(match[0])

                # 因为WWMI的形态键数量只有128个，这里shapekey_id是从0开始的，所以到127结束，所以不能大于等于128
                if shapekey_index >= 128:
                    break

                if shapekey_index not in shapekey_index_list:
                    # print("添加形态键Index: " + str(shapekey_index))
                    shapekey_index_list.append(shapekey_index)

                # 对于这个obj的每个顶点，我们都要尝试从当前shapekey中获取数据，如果获取到了，就放入缓存
                for vertex_index in range(len(mesh.vertices)):
                    base_vertex_coords = base_data[vertex_index].co
                    shapekey_vertex_coords = shapekey.data[vertex_index].co
                    vertex_offset = shapekey_vertex_coords - base_vertex_coords
                    # 到这里已经有vertex_id、shapekey_id、vertex_offset了，就不用像WWMI一样再从缓存读取了
                    offseted_vertex_index = vertex_index + vertex_count_offset

                    if offseted_vertex_index not in shapekey_data:
                        shapekey_data[offseted_vertex_index] = {}

                    # 如果相差太小，说明无效或者是一样的，说明这个顶点没有ShapeKey，此时向ShapeKeyOffsets中添加空的0
                    if vertex_offset.length < 0.000000001:
                        # print("相差太小，跳过处理。")
                        continue
                    
                    # 此时如果能获取到，说明有效，此时可以直接放入准备好的字典
                    shapekey_data[offseted_vertex_index][shapekey_index] = list(vertex_offset)

                # break
            # 对于每一个obj的每个顶点，都从0到128获取它的形态键对应偏移值
            vertex_count_offset = vertex_count_offset + len(mesh.vertices)
            # print("vertex_count_offset: " + str(vertex_count_offset))
        
        LOG.newline()

        # 转换格式问题
        shapekey_cache = {shapekey_id:{} for shapekey_id in shapekey_index_list}

        # 通过这种方式避免了必须合并obj的问题，总算是不用重构了。
        # TODO 我感觉这里少处理了什么，如果对应位置有形态键，但是跳过处理的话，这会不会炸掉？
        global_index_offset = 0
        global_vertex_offset = 0
        for obj_name, drawindexed_obj in self.obj_name_drawindexed_dict.items():
            obj = bpy.data.objects[obj_name]
            print("Processing obj: " + obj_name)
            mesh = obj.data

            # 获取当前obj每个Index对应的VertexId
            index_vertex_id_dict = self.__obj_name_index_vertex_id_dict[obj_name]
            for index_id,vertex_id in index_vertex_id_dict.items():
                # 这样VertexId加上全局偏移，就能获取到对应位置的形态键数据：
                vertex_shapekey_data = shapekey_data.get(vertex_id + global_vertex_offset, None)
                if vertex_shapekey_data is not None:
                    for shapekey_index,vertex_offsets in vertex_shapekey_data.items():
                        # 然后这里IndexId加上全局IndexId偏移，就得到了obj整体的IndexId，存到对应的ShapeKeyIndex上面
                        shapekey_cache[shapekey_index][index_id + global_index_offset] = vertex_offsets

            global_index_offset = global_index_offset + drawindexed_obj.UniqueVertexCount
            global_vertex_offset = global_vertex_offset + len(mesh.vertices)
        
            print("global_index_offset: " + str(global_index_offset))
            # print("global_vertex_offset: " + str(global_vertex_offset))
        LOG.newline()

        shapekey_verts_count = 0
        # 从0到128去获取ShapeKey的Index，有就直接加到
        for group_id in range(128):
            shapekey = shapekey_cache.get(group_id, None)
            if shapekey is None or len(shapekey_cache[group_id]) == 0:
                self.shapekey_offsets.extend([shapekey_verts_count if shapekey_verts_count != 0 else 0])
                continue

            self.shapekey_offsets.extend([shapekey_verts_count])

            for draw_index, vertex_offsets in shapekey.items():
                self.shapekey_vertex_ids.extend([draw_index])
                self.shapekey_vertex_offsets.extend(vertex_offsets + [0, 0, 0])
                shapekey_verts_count += 1

        # LOG.newline()
        # print("shapekey_offsets: " + str(len(self.shapekey_offsets))) # 128 WWMI:128
        # print("shapekey_vertex_ids: " + str(len(self.shapekey_vertex_ids))) # 29161 WWMI:29404
        # print("shapekey_vertex_offsets: " + str(len(self.shapekey_vertex_offsets))) # 174966  WWMI:29404 * 6  = 176424 * 2 = 352848
        # TimerUtils.End("read shapekey data")


    def __read_categoryname_bytelist_dict(self):
        # TimerUtils.Start("__read_categoryname_bytelist_dict")
        for component_name, model_collection_list in self.componentname_modelcollection_list_dict.items():
            for model_collection in model_collection_list:
                for obj_name in model_collection.obj_name_list:
                    category_buffer_list = self.__obj_name_category_buffer_list_dict.get(obj_name,None)
                    
                    if category_buffer_list is None:
                        print("Can't find vb object for " + obj_name +",skip this obj process.")
                        continue

                    for category_name in self.d3d11GameType.OrderedCategoryNameList:
                        

                        if category_name not in self.__categoryname_bytelist_dict:
                            self.__categoryname_bytelist_dict[category_name] =  category_buffer_list[category_name]
                        else:
                            existing_array = self.__categoryname_bytelist_dict[category_name]
                            buffer_array = category_buffer_list[category_name]

                            # 确保两个数组都是NumPy数组
                            existing_array = numpy.asarray(existing_array)
                            buffer_array = numpy.asarray(buffer_array)

                            # 使用 concatenate 连接两个数组，确保传递的是一个序列（如列表或元组）
                            concatenated_array = numpy.concatenate((existing_array, buffer_array))

                            # 更新字典中的值
                            self.__categoryname_bytelist_dict[category_name] = concatenated_array


                            # self.__categoryname_bytelist_dict[category_name] = numpy.concatenate(self.__categoryname_bytelist_dict[category_name],category_buffer_list[category_name])
        
        # 顺便计算一下步长得到总顶点数
        # print(self.d3d11GameType.CategoryStrideDict)
        position_stride = self.d3d11GameType.CategoryStrideDict["Position"]
        position_bytelength = len(self.__categoryname_bytelist_dict["Position"])
        self.draw_number = int(position_bytelength/position_stride)

        # TimerUtils.End("__read_categoryname_bytelist_dict")  
        # 耗时大概1S左右




    def combine_partname_ib_resource_and_filename_dict(self):
        '''
        拼接每个PartName对应的IB文件的Resource和filename,这样生成ini的时候以及导出Mod的时候就可以直接使用了。
        '''
        for partname in self.part_name_list:
            style_part_name = "Component" + partname
            ib_resource_name = "Resource_" + self.draw_ib + "_" + style_part_name
            ib_buf_filename = self.draw_ib + "-" + style_part_name + ".buf"
            self.PartName_IBResourceName_Dict[partname] = ib_resource_name
            self.PartName_IBBufferFileName_Dict[partname] = ib_buf_filename

    def write_buffer_files(self):
        '''
        导出当前Mod的所有Buffer文件
        '''
        buf_output_folder = GlobalConfig.path_generatemod_buffer_folder(draw_ib=self.draw_ib)
        # print("Write Buffer Files::")
        # Export Index Buffer files.
        for partname in self.part_name_list:
            component_name = "Component " + partname
            ib_buf = self.componentname_ibbuf_dict.get(component_name,None)

            if ib_buf is None:
                print("Export Skip, Can't get ib buf for partname: " + partname)
            else:
                ib_path = buf_output_folder + self.PartName_IBBufferFileName_Dict[partname]

                packed_data = struct.pack(f'<{len(ib_buf)}I', *ib_buf)
                with open(ib_path, 'wb') as ibf:
                    ibf.write(packed_data) 
            
            # 这里break是因为WWMI只需要一个IB文件
            if GlobalConfig.get_game_category() == GameCategory.UnrealVS or GlobalConfig.get_game_category() == GameCategory.UnrealCS: 
                break
            
        # print("Export Category Buffers::")
        # Export category buffer files.
        for category_name, category_buf in self.__categoryname_bytelist_dict.items():
            buf_path = buf_output_folder + self.draw_ib + "-" + category_name + ".buf"
            # print("write: " + buf_path)
            # print(type(category_buf[0]))
             # 将 list 转换为 numpy 数组
            # category_array = numpy.array(category_buf, dtype=numpy.uint8)
            with open(buf_path, 'wb') as ibf:
                category_buf.tofile(ibf)

        # 鸣潮的ShapeKey三个Buffer的导出
        if len(self.shapekey_offsets) != 0:
            with open(buf_output_folder + self.draw_ib + "-" + "ShapeKeyOffset.buf", 'wb') as file:
                for number in self.shapekey_offsets:
                    # 假设数字是32位整数，使用'i'格式符
                    # 根据实际需要调整数字格式和相应的格式符
                    data = struct.pack('i', number)
                    file.write(data)
        
        if len(self.shapekey_vertex_ids) != 0:
            with open(buf_output_folder + self.draw_ib + "-" + "ShapeKeyVertexId.buf", 'wb') as file:
                for number in self.shapekey_vertex_ids:
                    # 假设数字是32位整数，使用'i'格式符
                    # 根据实际需要调整数字格式和相应的格式符
                    data = struct.pack('i', number)
                    file.write(data)
        
        if len(self.shapekey_vertex_offsets) != 0:
            # 将列表转换为numpy数组，并改变其数据类型为float16
            float_array = numpy.array(self.shapekey_vertex_offsets, dtype=numpy.float32).astype(numpy.float16)
            
            # 以二进制模式写入文件
            with open(buf_output_folder + self.draw_ib + "-" + "ShapeKeyVertexOffset.buf", 'wb') as file:
                float_array.tofile(file)

