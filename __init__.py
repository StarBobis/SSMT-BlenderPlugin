

# UI界面
from .ui.panel_ui import * 
from .ui.panel_model_ui import *
from .ui.collection_rightclick_ui import *

# 自动更新功能
from . import addon_updater_ops


# 全局配置
from .properties.properties_dbmt_path import Properties_DBMT_Path
from .properties.properties_import_model import Properties_ImportModel
from .properties.properties_generate_mod import Properties_GenerateMod
from .properties.properties_wwmi import Properties_WWMI
from .properties.properties_extract_model import Properties_ExtractModel

from .migoto.migoto_import import *


bl_info = {
    "name": "SSMT",
    "description": "SSMT",
    "blender": (3, 6, 0),
    "version": (1, 6, 3),
    "location": "View3D",
    "category": "Generic"
}

class UpdaterPanel(bpy.types.Panel):
    """Update Panel"""
    bl_label = "检查版本更新"
    bl_idname = "Herta_PT_UpdaterPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = "objectmode"
    bl_category = "SSMT"
    bl_order = 99
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Call to check for update in background.
        # Note: built-in checks ensure it runs at most once, and will run in
        # the background thread, not blocking or hanging blender.
        # Internally also checks to see if auto-check enabled and if the time
        # interval has passed.
        # addon_updater_ops.check_for_update_background()
        col = layout.column()
        col.scale_y = 0.7
        # Could also use your own custom drawing based on shared variables.
        if addon_updater_ops.updater.update_ready:
            layout.label(text="There's a new update available!", icon="INFO")

        # Call built-in function with draw code/checks.
        # addon_updater_ops.update_notice_box_ui(self, context)
        addon_updater_ops.update_settings_ui(self, context)

class HertaUpdatePreference(bpy.types.AddonPreferences):
    # Addon updater preferences.
    bl_idname = __package__


    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=True) # type: ignore

    updater_interval_months: bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0) # type: ignore

    updater_interval_days: bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=1,
        min=0,
        max=31) # type: ignore

    updater_interval_hours: bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23) # type: ignore

    updater_interval_minutes: bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59) # type: ignore
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "auto_check_update")
        addon_updater_ops.update_settings_ui(self, context)


register_classes = (
    # 全局配置
    Properties_ImportModel,
    Properties_WWMI,
    Properties_DBMT_Path,
    Properties_GenerateMod,
    Properties_ExtractModel,

    # DBMT所在位置
    OBJECT_OT_select_dbmt_folder,

    # 导入3Dmigoto模型功能
    Import3DMigotoRaw,
    SSMTImportAllFromCurrentWorkSpace,
    # 生成Mod功能
    SSMTGenerateModHSR32,
    # DBMTExportUnityVSModToWorkSpaceSeperated,
    # DBMTExportUnityCSModToWorkSpaceSeperated,
    GenerateModWWMI,
    GenerateModYYSLS,
    SSMTGenerateModUnityCS,
    SSMTGenerateModUnityVS,
    GenerateModIdentityV,

    # 模型处理面板
    RemoveAllVertexGroupOperator,
    RemoveUnusedVertexGroupOperator,
    MergeVertexGroupsWithSameNumber,
    FillVertexGroupGaps,
    AddBoneFromVertexGroupV2,
    RemoveNotNumberVertexGroup,
    MMTResetRotation,
    CatterRightClickMenu,
    SplitMeshByCommonVertexGroup,
    RecalculateTANGENTWithVectorNormalizedNormal,
    RecalculateCOLORWithVectorNormalizedNormal,
    WWMI_ApplyModifierForObjectWithShapeKeysOperator,
    SmoothNormalSaveToUV,
    RenameAmatureFromGame,
    ModelSplitByLoosePart,
    ModelSplitByVertexGroup,
    ModelDeleteLoosePoint,
    ModelRenameVertexGroupNameWithTheirSuffix,
    ModelResetLocation,
    ModelSortVertexGroupByName,
    ModelVertexGroupRenameByLocation,

    # 集合的右键菜单栏
    Catter_MarkCollection_Switch,
    Catter_MarkCollection_Toggle,
    SSMT_LinkObjectsToCollection,
    SSMT_UnlinkObjectsFromCollection,
    # UI
    MigotoAttributePanel,
    PanelModelImportConfig,
    PanelGenerateModConfig,
    PanelButtons,
    # UpdaterPanel,
    PanelCollectionFunction,
    PanelModelProcess,

    ExtractSubmeshOperator,
    PanelModelSplit,

    HertaUpdatePreference,

    UpdaterPanel,
    # SSMT预备代码
    # PanelSSMTBasicConfig,
    # PanelSSMTExtractModel,
    # SSMTExtractModelGI,
    # SSMTExtractModelZZZ,
)


def register():
    for cls in register_classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.dbmt_path = bpy.props.PointerProperty(type=Properties_DBMT_Path)
    bpy.types.Scene.properties_wwmi = bpy.props.PointerProperty(type=Properties_WWMI)
    bpy.types.Scene.properties_import_model = bpy.props.PointerProperty(type=Properties_ImportModel)
    bpy.types.Scene.properties_generate_mod = bpy.props.PointerProperty(type=Properties_GenerateMod)
    bpy.types.Scene.properties_extract_model = bpy.props.PointerProperty(type=Properties_ExtractModel)

    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func_migoto_right_click)
    bpy.types.OUTLINER_MT_collection.append(menu_dbmt_mark_collection_switch)

    addon_updater_ops.register(bl_info)

    bpy.types.Scene.submesh_start = bpy.props.IntProperty(
        name="Start Index",
        default=0,
        min=0
    )
    bpy.types.Scene.submesh_count = bpy.props.IntProperty(
        name="Index Count",
        default=3,
        min=3
    )



def unregister():
    for cls in reversed(register_classes):
        bpy.utils.unregister_class(cls)

    # 卸载右键菜单
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func_migoto_right_click)
    bpy.types.OUTLINER_MT_collection.remove(menu_dbmt_mark_collection_switch)

    del bpy.types.Scene.submesh_start
    del bpy.types.Scene.submesh_count


if __name__ == "__main__":
    register()




