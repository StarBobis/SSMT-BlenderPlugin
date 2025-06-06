import bpy


class Catter_MarkCollection_Switch(bpy.types.Operator):
    bl_idname = "object.mark_collection_switch"
    bl_label = "分支:标记为按键切换类型"
    bl_description = "把当前选中集合标记为按键切换分支集合"

    def execute(self, context):
        if context.collection:
            context.collection.color_tag = "COLOR_04"
        return {'FINISHED'}


class Catter_MarkCollection_Toggle(bpy.types.Operator):
    bl_idname = "object.mark_collection_toggle"
    bl_label = "分支:标记为按键开关类型"
    bl_description = "把当前选中集合标记为按键开关分支集合"

    def execute(self, context):
        if context.collection:
            context.collection.color_tag = "COLOR_03"
        return {'FINISHED'}
    
class SSMT_LinkObjectsToCollection(bpy.types.Operator):
    bl_idname = "object.link_objects_to_collection"
    bl_label = "链接:链接物体到集合"
    bl_description = "将选中的物体链接到当前选中的集合"

    def execute(self, context):
        # 获取选中的物体
        selected_objects = bpy.context.selected_objects

        # 获取最后选中的集合（通过视图层的活动层集合）
        if bpy.context.view_layer.active_layer_collection:
            target_collection = bpy.context.view_layer.active_layer_collection.collection
        else:
            target_collection = None

        # 检查是否有选中的物体和集合
        if not selected_objects:
            raise Exception("请先选择一个或多个物体")
        if not target_collection:
            raise Exception("请最后选中一个目标集合")

        # 将选中的物体链接到目标集合
        for obj in selected_objects:
            # 确保物体不在目标集合中
            if obj.name not in target_collection.objects:
                target_collection.objects.link(obj)

        print(f"已将 {len(selected_objects)} 个物体链接到集合 '{target_collection.name}'")
        return {'FINISHED'}

class SSMT_UnlinkObjectsFromCollection(bpy.types.Operator):
    bl_idname = "object.unlink_objects_from_collection"
    bl_label = "链接:从集合中移除选中的链接物体"
    bl_description = "将选中的物体从当前选中的集合中移除"

    def execute(self, context):
        """从活动集合中移除选中的物体"""
        # 获取选中的物体
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            print("没有选中的物体")
            return
        
        # 获取活动集合（最后选中的集合）
        if bpy.context.view_layer.active_layer_collection:
            target_collection = bpy.context.view_layer.active_layer_collection.collection
        else:
            print("请先在大纲视图中选中目标集合")
            return
        
        # 从活动集合中移除选中的物体
        unlinked_count = 0
        for obj in selected_objects:
            # 确保物体在目标集合中
            if obj.name in target_collection.objects:
                target_collection.objects.unlink(obj)
                unlinked_count += 1
        
        print(f"已从集合 '{target_collection.name}' 移除 {unlinked_count} 个物体")
        return {'FINISHED'}
    


def menu_dbmt_mark_collection_switch(self, context):
    self.layout.separator()
    self.layout.operator(Catter_MarkCollection_Toggle.bl_idname)
    self.layout.operator(Catter_MarkCollection_Switch.bl_idname)
    self.layout.operator(SSMT_LinkObjectsToCollection.bl_idname)
    self.layout.operator(SSMT_UnlinkObjectsFromCollection.bl_idname)



class PanelCollectionFunction(bpy.types.Panel):
    '''
    集合的右键菜单的UI面板，相比于默认的右键菜单更省事儿
    '''
    bl_label = "集合操作" 
    bl_idname = "VIEW3D_PT_SSMT_CollectionFunction_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SSMT'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        layout.operator(Catter_MarkCollection_Toggle.bl_idname)
        layout.operator(Catter_MarkCollection_Switch.bl_idname)
        layout.operator(SSMT_LinkObjectsToCollection.bl_idname)
        layout.operator(SSMT_UnlinkObjectsFromCollection.bl_idname)