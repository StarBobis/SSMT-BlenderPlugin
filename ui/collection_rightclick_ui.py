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
    bl_label = "分支:链接物体到集合"
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



def menu_dbmt_mark_collection_switch(self, context):
    self.layout.separator()
    self.layout.operator(Catter_MarkCollection_Toggle.bl_idname)
    self.layout.operator(Catter_MarkCollection_Switch.bl_idname)
    self.layout.operator(SSMT_LinkObjectsToCollection.bl_idname)
