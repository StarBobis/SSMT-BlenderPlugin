import bpy

from ..config.main_config import GlobalConfig

class ModelCollection:
    def __init__(self):
        self.type = ""
        self.model_collection_name = ""
        self.obj_name_list:list[str] = []


class CollectionUtils:
    @classmethod
    def get_collection_by_name(cls,collection_name:str):
        """
        根据集合名称获取集合对象。

        :param collection_name: 要获取的集合名称
        :return: 返回找到的集合对象，如果未找到则返回 None
        """
        # 尝试从 bpy.data.collections 获取指定名称的集合
        if collection_name in bpy.data.collections:
            return bpy.data.collections[collection_name]
        else:
            print(f"未找到名称为 '{collection_name}' 的集合")
            return None
    
    # Recursive select every object in a collection and it's sub collections.
    @classmethod
    def select_collection_objects(cls,collection):
        def recurse_collection(col):
            for obj in col.objects:
                obj.select_set(True)
            for subcol in col.children_recursive:
                recurse_collection(subcol)

        recurse_collection(collection)

    @classmethod
    def find_layer_collection(cls,view_layer, collection_name):
        def recursive_search(layer_collections, collection_name):
            for layer_collection in layer_collections:
                if layer_collection.collection.name == collection_name:
                    return layer_collection
                found = recursive_search(layer_collection.children, collection_name)
                if found:
                    return found
            return None

        return recursive_search(view_layer.layer_collection.children, collection_name)

    @classmethod
    def get_collection_properties(cls,collection_name:str):
        # Nico: Blender Gacha: 
        # Can't get collection's property by bpy.context.collection or it's children or any of children's children.
        # Can only get it's property by search it recursively in bpy.context.view_layer  

        # 获取当前活动的视图层
        view_layer = bpy.context.view_layer

        # 查找指定名称的集合
        collection1 = bpy.data.collections.get(collection_name,None)
        
        if not collection1:
            print(f"集合 '{collection_name}' 不存在")
            return None

        # 递归查找集合在当前视图层中的层集合对象
        layer_collection = CollectionUtils.find_layer_collection(view_layer, collection_name)

        if not layer_collection:
            print(f"集合 '{collection_name}' 不在当前视图层中")
            return None

        # 获取集合的实际属性
        hide_viewport = layer_collection.hide_viewport
        exclude = layer_collection.exclude

        return {
            'name': collection1.name,
            'hide_viewport': hide_viewport,
            'exclude': exclude
        }
    
    @classmethod
    def is_collection_visible(cls,collection_name:str):
        '''
        判断collection是否可见，可见的状态是不隐藏且勾选上
        '''
        collection_property = CollectionUtils.get_collection_properties(collection_name)

        if collection_property is not None:
            if collection_property["hide_viewport"]:
                return False
            if collection_property["exclude"]:
                return False
            else:
                return True
        else:
            return False
    
    @classmethod
    # get_collection_name_without_default_suffix
    def get_clean_collection_name(cls,collection_name:str):
        if "." in collection_name:
            new_collection_name = collection_name.split(".")[0]
            return new_collection_name
        else:
            return collection_name

    @classmethod
    def new_workspace_collection(cls):
        '''
        创建一个WorkSpace名称为名称的集合并返回此集合，WorkSpace集合的颜色是COLOR_01        
        '''
        workspace_collection = bpy.data.collections.new(GlobalConfig.workspacename)
        workspace_collection.color_tag = "COLOR_01"
        return workspace_collection
    
    @classmethod
    def new_draw_ib_collection(cls,collection_name:str):
        draw_ib_collection = bpy.data.collections.new(collection_name)
        draw_ib_collection.color_tag = "COLOR_07" #粉色
        return draw_ib_collection
    
    @classmethod
    def new_component_collection(cls,component_name:str):
        component_collection = bpy.data.collections.new(component_name)
        component_collection.color_tag = "COLOR_05" #蓝色
        return component_collection
    
    @classmethod
    def new_switch_collection(cls,collection_name:str):
        '''
        创建一个按键切换集合，是绿色的，COLOR_04
        '''
        switch_collection = bpy.data.collections.new(collection_name)
        switch_collection.color_tag = "COLOR_04" #绿色
        return switch_collection


    @classmethod
    def is_valid_workspace_collection(cls,workspace_collection) -> str:
        '''
        按下生成Mod按钮之后，要判断当前选中的集合是否为工作空间集合，并且给出报错信息
        所以在这里进行校验，如果有问题就返回对应的报错信息，如果没有就返回空字符串
        在外面接收结果，判断如果不是空字符串就report然后返回，是空字符串才能继续执行。
        '''
        if len(workspace_collection.children) == 0:
            return "当前选中的集合没有任何子集合，不是正确的工作空间集合"

        for draw_ib_collection in workspace_collection.children:
            # Skip hide collection.
            if not CollectionUtils.is_collection_visible(draw_ib_collection.name):
                continue

            # get drawib
            draw_ib_alias_name = CollectionUtils.get_clean_collection_name(draw_ib_collection.name)
            if "_" not in draw_ib_alias_name:
                return "当前选中集合中的DrawIB集合名称被意外修改导致无法识别到DrawIB\n1.请不要修改导入时以drawib_aliasname为名称的集合\n2.请确认您是否正确选中了工作空间集合."
        
            # 如果当前集合没有子集合，说明不是一个合格的分支Mod
            if len(draw_ib_collection.children) == 0:
                return "当前选中集合不是一个标准的分支模型集合，请检查您是否以分支集合方式导入了模型: " + draw_ib_collection.name + " 未检测到任何子集合"
            
            for component_collection in draw_ib_collection.children:
                if len(component_collection.children) == 0:
                    return "当前选中集合不是一个标准的分支模型集合，请检查您是否以分支集合方式导入了模型: " + component_collection.name + "未检测到任何子集合"

        return ""
    
    @classmethod
    def parse_drawib_collection_architecture(cls,draw_ib_collection):
        '''
        解析工作空间集合架构，得到方便后续访问使用的抽象数据类型ModelCollection。
        返回 componentname_modelcollection_list_dict
        '''
        componentname_modelcollection_list_dict:dict[str,list[ModelCollection]] = {}

        for component_collection in draw_ib_collection.children:
            # 从集合名称中获取导出后部位的名称，如果有.001这种自动添加的后缀则去除掉
            component_name = CollectionUtils.get_clean_collection_name(component_collection.name)

            model_collection_list = []
            for m_collection in component_collection.children:
                # 如果模型不可见则跳过。
                if not CollectionUtils.is_collection_visible(m_collection.name):
                    print("Skip " + m_collection.name + " because it's invisiable.")
                    continue

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

            componentname_modelcollection_list_dict[component_name] = model_collection_list
        
        return componentname_modelcollection_list_dict
    
    @classmethod
    def parse_key_number(cls,draw_ib_collection) -> int:
        '''
        提前统计好当前集合架构中有多少个Key要声明
        '''
        componentname_modelcollection_list_dict = cls.parse_drawib_collection_architecture(draw_ib_collection=draw_ib_collection)

        tmp_number = 0
        for model_collection_list in componentname_modelcollection_list_dict.values():
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
        
        return tmp_number